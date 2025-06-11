from django.shortcuts import render, redirect
from django.utils import timezone

import pymysql
from .models import Project

# Create your views here.

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

        if not selected_columns:
            return render(request, 'select_table.html', {'error': '필드를 하나 이상 선택해주세요.'})

        request.session['selected_tables'] = selected_tables
        request.session['selected_columns'] = selected_columns

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
    selected_columns = request.session.get('selected_columns')
    if not selected_columns:
        return redirect('select_table')

    # 테이블별로 컬럼 정리
    columns_by_table = {}
    for col in selected_columns:
        try:
            table_name, column_name = col.split('.', 1)
        except ValueError:
            continue  # 포맷이 이상할 경우 스킵

        if table_name not in columns_by_table:
            columns_by_table[table_name] = []

        columns_by_table[table_name].append({
            'field': column_name,
            'ai_meaning': '',
            'ai_reason': '',
        })

    return render(request, 'analyze.html', {'columns_by_table': columns_by_table})

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
