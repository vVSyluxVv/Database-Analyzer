from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponse

import pymysql
from .models import Project
from openai import OpenAI
from difflib import get_close_matches
import io
# Create your views here.

client=OpenAI()

def dummy(request):
    return render(request, 'base.html')

def home(request):
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'home.html', {'projects': projects})

def connect_db(request):
    if request.method == 'POST':
        host = request.POST.get('host')
        port = request.POST.get('port')
        dbname = request.POST.get('dbname')
        user = request.POST.get('user')
        password = request.POST.get('password')

        try:
            connection = pymysql.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=dbname,
                cursorclass=pymysql.cursors.DictCursor
            )
            with connection.cursor() as cursor:
                # 테이블 개수
                cursor.execute("SHOW TABLES;")
                tables = cursor.fetchall()
                table_count = len(tables)

                # 전체 컬럼 수 계산
                total_columns = 0
                for table in tables:
                    table_column = list(table.values())[0]
                    cursor.execute(f"DESCRIBE `{table_column}`;")
                    columns = cursor.fetchall()
                    total_columns += len(columns)

            connection.close()

            # Project 저장
            Project.objects.create(
                db_name=dbname,
                table_count=table_count,
                column_count=total_columns
            )

            request.session['db_config'] = {
                'host': host,
                'port': port,
                'dbname': dbname,
                'user': user,
                'password': password,
            }

            return redirect('select_table')

        except Exception as e:
            error_message = f"DB 연결 실패: {str(e)}"
            return render(request, 'connect_db.html', {'error': error_message})

    return render(request, 'connect_db.html')

def select_table(request):
    db_config = request.session.get('db_config')
    if not db_config:
        return redirect('connect_db')

    if request.method == 'POST':
        selected_tables = request.POST.getlist('selected_tables')
        selected_columns = request.POST.getlist('selected_columns')
        gpt_prompt = request.POST.get('gpt_prompt', '')  # 🧠 프롬프트 수집

        if not selected_tables or not selected_columns:
            return render(request, 'select_table.html', {'error': '테이블과 필드를 하나 이상 선택해주세요.'})

        # ✅ 세션 저장
        request.session['selected_tables'] = selected_tables
        request.session['selected_columns'] = selected_columns
        request.session['gpt_prompt'] = gpt_prompt  # 👉 세션에 저장

        return redirect('analyze')


    # GET 요청 처리: 테이블 목록 가져오기
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['dbname'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            result = cursor.fetchall()
            if result:
                table_column = list(result[0].keys())[0]
                tables = [row[table_column] for row in result]
            else:
                tables = []
            # 테이블별 컬럼 가져오기
            columns_info = {}
            for table in tables:
                cursor.execute(f"DESCRIBE `{table}`;")
                columns = cursor.fetchall()
                columns_info[table] = columns
    except Exception as e:
        tables = []
        columns_info = {}
        print(f"테이블 목록 가져오기 실패: {e}")

    return render(request, 'select_table.html', {'columns_info': columns_info})

def analyze(request):
    selected_tables = request.session.get('selected_tables', [])
    selected_columns = request.session.get('selected_columns', [])
    gpt_prompt = request.session.get('gpt_prompt', '').strip()

    if not selected_tables or not selected_columns:
        return redirect('select_table')

    if not gpt_prompt:
        gpt_prompt = (
            "전체 데이터베이스의 요약에 기반해 선택된 테이블의 필드값들의 의미를 유추하고 "
            "그 과정을 간단히 요약하시오."
        )

    # 🧩 테이블별 컬럼 정리
    columns_by_table = {}
    for col in selected_columns:
        table_name, column_name = col.split('.', 1)
        columns_by_table.setdefault(table_name, []).append({
            'field': column_name,
            'ai_meaning': '',
            'ai_reason': '',
        })

    try:
        # 📡 GPT 프롬프트 구성
        full_prompt = "아래는 사용자가 선택한 데이터베이스의 테이블과 컬럼입니다:\n\n"
        for table, cols in columns_by_table.items():
            full_prompt += f"[테이블: {table}]\n"
            full_prompt += ", ".join([c['field'] for c in cols]) + "\n\n"

        full_prompt += f"사용자 요청:\n{gpt_prompt}\n\n"
        full_prompt += (
            "각 컬럼에 대해 (1) 추정 의미와 (2) 추론 이유를 표 형식으로 알려주세요.\n\n"
            "[응답 형식 예시]\n"
            "products.price | 제품 가격 | 가격 관련 숫자 데이터입니다.\n"
            "categories.name | 카테고리 이름 | 이름 문자열로 보입니다.\n"
            "(1) 추정 의미 의 경우 Primary Key, Foreign Key 등 관계를 간단히 표시해주세요.\n"
            "이와 같이 표 형식으로 응답해주세요. 불필요한 설명 없이 표만 출력해주세요."
        )

        # 🔗 GPT 요청
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 데이터 구조와 의미를 추론하는 전문가입니다."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.2
        )

        gpt_answer = response.choices[0].message.content
        print("=== [GPT 응답 원문] ===\n", gpt_answer)

        # 📦 응답 파싱
        parsed = {}
        lines = gpt_answer.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("|---") or "컬럼명" in line or "테이블 및" in line:
                continue

            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                col_key = parts[0].strip().lower().replace("`", "").replace(" ", "")
                parsed[col_key] = {
                    'ai_meaning': parts[1].strip(),
                    'ai_reason': parts[2].strip()
                }

        print("=== [파싱 결과] ===")
        for k, v in parsed.items():
            print(f" → {k}: {v}")

        # 🎯 결과 적용
        for table, cols in columns_by_table.items():
            for col in cols:
                full_key = f"{table}.{col['field']}".lower().replace(" ", "")
                short_key = col['field'].lower().replace(" ", "")
                match = parsed.get(full_key) or parsed.get(short_key)

                if match:
                    col['ai_meaning'] = match['ai_meaning']
                    col['ai_reason'] = match['ai_reason']
                else:
                    col['ai_meaning'] = '(응답 없음)'
                    col['ai_reason'] = '(해당 필드에 대한 분석 결과 없음)'

    except Exception as e:
        print(f"[GPT 분석 실패] {e}")
        for table, cols in columns_by_table.items():
            for col in cols:
                col['ai_meaning'] = '(분석 실패)'
                col['ai_reason'] = str(e)

    request.session['analysis_result'] = columns_by_table

    return render(request, 'analyze.html', {
        'columns_by_table': columns_by_table
    })

def download_analysis(request):
    columns_by_table = request.session.get('analysis_result')

    if not columns_by_table:
        return HttpResponse("분석 결과가 없습니다.", content_type="text/plain")

    buffer = io.StringIO()
    buffer.write("AI 분석 결과 요약\n\n")

    for table, columns in columns_by_table.items():
        buffer.write(f"[테이블: {table}]\n")
        buffer.write("컬럼명 | 추정 의미 | 추론 이유\n")
        buffer.write("-" * 50 + "\n")
        for col in columns:
            buffer.write(f"{col['field']} | {col['ai_meaning']} | {col['ai_reason']}\n")
        buffer.write("\n")

    response = HttpResponse(buffer.getvalue(), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="analysis_result.txt"'
    return response

def view_table(request):
    db_config = request.session.get('db_config')

    if not db_config:
        return redirect('connect_db')

    table_name = request.GET.get('table')  # 선택된 테이블명

    tables = []
    columns = []
    rows = []

    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['dbname'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            # 테이블 목록
            cursor.execute("SHOW TABLES;")
            result = cursor.fetchall()
            if result:
                table_column = list(result[0].keys())[0]
                tables = [row[table_column] for row in result]

            # 특정 테이블 조회
            if table_name:
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 100;")
                rows = cursor.fetchall()
                if rows:
                    columns = rows[0].keys()
                else:
                    # 컬럼만 조회
                    cursor.execute(f"DESCRIBE `{table_name}`;")
                    columns = [col['Field'] for col in cursor.fetchall()]
    except Exception as e:
        print(f"테이블 뷰어 오류: {e}")

    return render(request, 'view_table.html', {
        'tables': tables,
        'selected_table': table_name,
        'columns': columns,
        'rows': rows,
    })

def database_summary_and_erd(request):
    db_config = request.session.get('db_config')
    if not db_config:
        return redirect('connect_db')

    summary_text = ''
    erd_text = ''

    try:
        import pymysql

        connection = pymysql.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['dbname'],
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            # 전체 테이블 목록 가져오기
            cursor.execute("SHOW TABLES;")
            tables_raw = cursor.fetchall()
            table_column = list(tables_raw[0].keys())[0]
            tables = [row[table_column] for row in tables_raw]

            schema_info = ""
            for table in tables:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
                columns = cursor.fetchall()
                schema_info += f"[{table}]\n"
                for col in columns:
                    schema_info += f"  - {col['Field']} ({col['Type']})\n"
                schema_info += "\n"

        # GPT 프롬프트 구성
        gpt_prompt = (
            "다음은 MySQL 데이터베이스의 테이블과 컬럼 정보입니다.\n"
            "이 정보를 바탕으로:\n"
            "1. 전체 DB에 대한 한 줄 요약을 먼저 제시하고,\n"
            "2. 테이블 간 관계를 ASCII 형식으로 ERD 다이어그램처럼 보여주세요.\n"
            "3. Primary Key, Foreign Key 등 관계를 명확히 표시해주세요.\n"
            "관계 유추가 어려울 경우, 주요 키/컬럼 이름 유사성을 바탕으로 추정해주세요.\n\n"
            f"{schema_info}"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 데이터베이스 설계 전문가입니다."},
                {"role": "user", "content": gpt_prompt}
            ],
            temperature=0.3
        )

        gpt_answer = response.choices[0].message.content.strip()
        print("=== GPT ERD 응답 ===\n", gpt_answer)

        # 결과 나누기 (요약 / 다이어그램)
        if "\n" in gpt_answer:
            lines = gpt_answer.splitlines()
            summary_text = lines[0]
            erd_text = "\n".join(lines[1:])
        else:
            summary_text = "요약 없음"
            erd_text = gpt_answer

    except Exception as e:
        summary_text = "GPT 요약 실패"
        erd_text = str(e)

    return render(request, 'erd_view.html', {
        'summary': summary_text,
        'erd': erd_text,
    })