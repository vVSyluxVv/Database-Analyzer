from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import os

from openai import OpenAI
client = OpenAI()

llm = ChatOpenAI(model_name="GPT-4o", temperature=0.2)

prompt = PromptTemplate(
    input_variables=["column_name", "sample_values"],
    template="""
You are an expert data analyst.
The following is a table and a column from the database.
Table: {table_name}
Column: {column_name}
Infer the meaning of the column and explain the reason of the inference briefly.
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

def analyze_column(column_name, sample_values):
    return chain.run({
        "column_name": column_name,
        "sample_values": sample_values
    })
    