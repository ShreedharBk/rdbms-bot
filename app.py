import streamlit as st
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import re
import time

# Load environment variables
load_dotenv()

# Streamlit UI
st.title("🔍 RDBMS Chatbot")
st.subheader("Ask questions in plain English and get direct answers")

# Supported Groq models
GROQ_MODELS = [
    "llama3-70b-8192",
    "llama3-8b-8192"
]

# Model selection
st.sidebar.header("Model Provider")
model_provider = st.sidebar.radio("Choose your LLM provider", ("OpenAI", "Groq"))

# Model selection depending on provider
if model_provider == "Groq":
    selected_model = st.sidebar.selectbox("Select Groq Model", GROQ_MODELS)
else:
    selected_model = "gpt-3.5-turbo"

# API key input
api_key = st.sidebar.text_input(f"{model_provider} API Key", type="password")

# Validate API key
if not api_key:
    st.error(f"{model_provider} API key is required.")
    st.stop()

# Initialize client based on selected provider
client = None
if model_provider == "OpenAI":
    import openai
    openai.api_key = api_key
    client = openai.OpenAI()
elif model_provider == "Groq":
    try:
        import groq
        client = groq.Groq(api_key=api_key)
    except ModuleNotFoundError:
        st.error("Groq module not found. Install it via `pip install groq`.")
        st.stop()

# Function to clean SQL response
def clean_sql_response(sql_response):
    sql_response = re.sub(r'```sql|```', '', sql_response)
    sql_response = sql_response.strip()
    if sql_response.endswith(';'):
        sql_response = sql_response[:-1]
    return sql_response

# Sidebar for DB connection
st.sidebar.header("Database Connection")
db_user = st.sidebar.text_input("User", "root")
db_pass = st.sidebar.text_input("Password", type="password")
db_host = st.sidebar.text_input("Host", "localhost")
db_name = st.sidebar.text_input("Database", "test")

# Initialize session state
if 'conn' not in st.session_state:
    st.session_state.conn = None
if 'tables' not in st.session_state:
    st.session_state.tables = []
if 'question' not in st.session_state:
    st.session_state.question = ""
if 'answer' not in st.session_state:
    st.session_state.answer = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Connect to database
if st.sidebar.button("Connect to MySQL"):
    try:
        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}/{db_name}")
        st.session_state.conn = engine.connect()
        st.success(f"Connected to {db_name} successfully!")
        tables = pd.read_sql("SHOW TABLES", st.session_state.conn)
        st.session_state.tables = tables.iloc[:, 0].tolist()
    except Exception as e:
        st.error(f"Connection failed: {str(e)}")

# Clear history function
def clear_chat_history():
    st.session_state.chat_history = []
    st.session_state.answer = None
    st.session_state.question = ""
    st.rerun()

# Add clear history button to sidebar at the bottom
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Chat History", help="Clear all chat history"):
    clear_chat_history()

# If connected, show query interface
if st.session_state.conn:
    st.subheader("Ask Your Question")
   
    question = st.text_input(
        "Enter your question (e.g., 'Show all products with price > 500')",
        value=st.session_state.question
    )

    if st.button("Get Answer") and question:
        st.session_state.question = question

        start_time = time.time()

        with st.spinner("Analyzing your question..."):
            try:
                table_list = st.session_state.tables
                sample_data_snippets = []

                for table in table_list:
                    try:
                        schema = pd.read_sql(f"DESCRIBE {table}", st.session_state.conn)
                        sample_data = pd.read_sql(f"SELECT * FROM {table} LIMIT 3", st.session_state.conn)
                        sample_data_snippets.append(f"\nTable `{table}`:\nSchema:\n{schema.to_markdown()}\nSample Data:\n{sample_data.to_markdown()}")
                    except Exception as e:
                        sample_data_snippets.append(f"\nTable `{table}` could not be described or sampled: {str(e)}")

                sql_prompt = f"""
                Convert this natural language question to valid MySQL SQL.
                The database contains the following tables:
                {', '.join(table_list)}

                You can use any relevant tables needed to answer the question. Avoid SELECT *. Explicitly list all columns with table aliases, and use alias names to avoid duplicate column names.
                If the user's question contains both a counting/statistical intent and a listing/detail intent, return two separate SQL queries: for example: one for the count, and one to list the details. This improves clarity and avoids SQL errors.
                
                Important: Use only valid SQL compatible with MySQL's ONLY_FULL_GROUP_BY mode. Do not include non-aggregated columns in SELECT unless they appear in GROUP BY. Use GROUP_CONCAT() for lists.

                Table structures and sample data:
                {''.join(sample_data_snippets)}
                
                Question:
                {question}
                
                Return only the final executable SQL query.
                """

                sql_response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "You are a SQL expert. Return only required executable SQL without any extra words."},
                        {"role": "user", "content": sql_prompt}
                    ],
                    temperature=0
                )

                # Start timing
                start_time = time.time()

                generated_sql = sql_response.choices[0].message.content
                cleaned_sql = clean_sql_response(generated_sql)


                # Handle multiple queries
                queries = [q.strip() for q in cleaned_sql.split(';') if q.strip()]
                result_set = []

                for q in queries:
                    try:
                        df = pd.read_sql(q, st.session_state.conn)
                        result_set.append((q, df))
                    except Exception as ex:
                        result_set.append((q, f"Error executing this query: {str(ex)}"))
                
                # Stop timing
                execution_time = round((time.time() - start_time) * 1000, 2)  # in milliseconds
                total_rows = sum(len(df) for _, df in result_set if isinstance(df, pd.DataFrame))

                # Compose markdown for the AI summary prompt
                result_markdown = "\n\n".join(
                    f"Query:\n```sql\n{q}\n```\n\nResult:\n{df.to_markdown(index=False) if isinstance(df, pd.DataFrame) else df}"
                    for q, df in result_set
                )

                answer_prompt = f"""
                The user asked: {question}

                Below are the SQL results:

                {result_markdown}

                Provide a natural language summary explaining what the results show.
                """

                answer_response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful data analyst."},
                        {"role": "user", "content": answer_prompt}
                    ],
                    temperature=0.3
                )

                st.session_state.answer = {
                    "question": question,
                    "sql": queries,
                    "results": result_set,
                    "answer": answer_response.choices[0].message.content,
                    "execution_time": execution_time,
                    "total_rows": total_rows
                }

                st.session_state.chat_history.append({
                "user": question,
                "sql": cleaned_sql,
                "answer": answer_response.choices[0].message.content,
                "execution_time": execution_time,
                "total_rows": total_rows
                })

            except Exception as e:
                st.error(f"Error processing your question: {str(e)}")

    if st.session_state.answer:   

        st.subheader("Answer")
        cleaned_answer = st.session_state.answer["answer"].replace('\n', ' ').strip()
        st.write(cleaned_answer)
        
        # Retrieve and show execution info from session_state
        col1, col2 = st.columns(2)

        with col1:
            st.info(f"⏱️ Query executed in {st.session_state.answer['execution_time']} ms")

        with col2:
            st.info(f"🔢 Total rows returned: {st.session_state.answer['total_rows']}")

        if st.checkbox("Show technical details"):
            for i, (q, df) in enumerate(st.session_state.answer["results"], start=1):
                st.subheader(f"Query {i}")
                st.code(q, language="sql")
                if isinstance(df, pd.DataFrame):
                    st.dataframe(df)
                else:
                    st.error(df)
        
        st.subheader("---------------------------------------------------------------------")

        st.subheader("🗂️ Chat History")

        for chat in st.session_state.chat_history:
            with st.container():
                st.markdown(f"**🧑‍💻 You:** {chat['user']}")
                #st.markdown(f"**🤖 Bot:** {chat['answer']}")
                st.markdown(f"`⏱️ {chat['execution_time']} ms` &nbsp;&nbsp; `🔢 {chat['total_rows']} rows`")
                st.markdown("---")
                
# Sidebar instructions
st.sidebar.markdown("""
**Instructions:**
1. Select LLM provider (OpenAI or Groq)
2. Enter API key
3. Enter MySQL credentials
4. Click "Connect to MySQL"
5. Ask your question in plain English
6. Get direct answer automatically

**Example Questions:**
- Show all products with price > 500  
- What is field_id of product smartphone Y?  
- Count products in each category  
""")
