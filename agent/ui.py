import asyncio

import streamlit as st

from agent import ask, build_agent

st.set_page_config(page_title="Football Analyst", page_icon="⚽")
st.title("Premier League Analyst")
st.caption("Ask in plain English. Answers come from a Postgres database refreshed daily.")

EXAMPLES = [
    "Who is top of the league?",
    "Who has the best home record?",
    "What is Arsenal's form over the last 5 games?",
    "Who are the top 5 scorers and how many goals per match?",
    "What are the upcoming fixtures for Chelsea?",
]


@st.cache_resource
def get_agent():
    return asyncio.run(build_agent())


def clean(text):
    # stop Streamlit reading dollar signs as LaTeX
    return text.replace("$", "\\$")


def show_sql(queries):
    if queries:
        with st.expander("SQL used"):
            for q in queries:
                st.code(q, language="sql")


agent = get_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Try asking")
    for example in EXAMPLES:
        if st.button(example):
            st.session_state.pending = example
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(clean(m["content"]))
        show_sql(m.get("sql"))

question = st.chat_input("Ask about the Premier League") or st.session_state.pop("pending", None)

if question:
    history = [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(clean(question))

    with st.chat_message("assistant"):
        with st.spinner("Querying the database..."):
            answer, queries = asyncio.run(ask(agent, question, history))
        st.markdown(clean(answer))
        show_sql(queries)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sql": queries})