import asyncio
import os

import streamlit as st

from agent import ask, load_agent_parts, make_agent

# on Streamlit Cloud, secrets come from st.secrets, so copy them into the environment
for key in ("READONLY_DATABASE_URL", "GROQ_API_KEY", "FREE_MODEL"):
    try:
        if key not in os.environ and key in st.secrets:
            os.environ[key] = st.secrets[key]
    except Exception:
        pass  # no secrets file when running locally

st.set_page_config(page_title="Football Analyst", page_icon="⚽")
st.title("Premier League Analyst ⚽️")
st.caption("Ask in plain English. Answers come from a Postgres database refreshed daily.")

EXAMPLES = [
    "Who is top of the league?",
    "Who has the best home record?",
    "What is Arsenal's form over the last 5 games?",
    "Who are the top 5 scorers and how many goals per match?",
    "What are the upcoming fixtures for Chelsea?",
]


@st.cache_resource
def get_parts():
    return asyncio.run(load_agent_parts())


def clean(text):
    # stop Streamlit reading dollar signs as LaTeX
    return text.replace("$", "\\$")


def show_sql(queries):
    if queries:
        with st.expander("SQL used"):
            for q in queries:
                st.code(q, language="sql")


tools, prompt = get_parts()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Model")
    mode = st.radio("Choose a model", ["Free model (limited)", "My OpenAI key"],
                    label_visibility="collapsed")
    free = mode.startswith("Free")
    typed_key = ""
    if free:
        st.caption("A free shared model. It can be busy when several people ask at once.")
    else:
        typed_key = st.text_input("Your OpenAI API key", type="password", placeholder="sk-...")
        st.caption("Used only for your questions in this session. It is not stored or logged.")

    st.header("Try asking")
    for example in EXAMPLES:
        if st.button(example):
            st.session_state.pending = example
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# a pasted key wins, the environment key is for local use
api_key = typed_key or os.getenv("OPENAI_API_KEY")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(clean(m["content"]))
        show_sql(m.get("sql"))

if not free and not api_key:
    st.session_state.pop("pending", None)
    st.info("Paste your OpenAI API key in the sidebar, or switch to the free model.")
    st.chat_input("Add your API key to chat", disabled=True)
    st.stop()

question = st.chat_input("Ask about the Premier League") or st.session_state.pop("pending", None)

if question:
    history = [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(clean(question))

    with st.chat_message("assistant"):
        try:
            with st.spinner("Querying the database..."):
                agent = make_agent(tools, prompt, api_key, free=free)
                answer, queries = asyncio.run(ask(agent, question, history))
        except Exception as e:
            # never show the raw error, it can contain account details or part of a key
            queries = []
            text = str(e).lower()
            if "429" in text or "rate" in text:
                answer = ("The free model is busy right now. Wait a minute and try again, "
                          "or switch to My OpenAI key in the sidebar.")
            else:
                answer = "Something went wrong. If you are using your own key, check that it is valid and has credit."
        st.markdown(clean(answer))
        show_sql(queries)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sql": queries})