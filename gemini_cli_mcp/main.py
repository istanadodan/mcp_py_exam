import streamlit as st
from src.fastmcp.mcp_client3 import get_gemini_client
from dotenv import load_dotenv
import asyncio

load_dotenv()


@st.cache_resource
async def get_cached_client():
    return await get_gemini_client()  # 최초 1회만 실행


async def ask_llm2(user_query: str) -> str:
    client = await get_cached_client()
    return await client.chat(user_query)


# OpenAI 클라이언트 준비
async def ask_llm(user_query: str) -> str:
    client = await get_gemini_client()
    if client is None:
        return "서버에 연결하지 못했습니다."
    result = await client.chat(user_query)
    await client.cleanup()
    return result


# 페이지 레이아웃
st.set_page_config(page_title="LLM Query Demo", layout="centered")

st.title("🔎 LLM Query Demo")
st.write("LLM에게 질문을 보내고 답변을 받아보세요.")

# 사용자 입력
query = st.text_area("질문을 입력하세요:", height=120)

# 버튼 클릭 시 LLM 호출
# Streamlit 1.50.0에서는 직접 await 사용 불가
# asyncio.run()도 이미 이벤트 루프가 실행 중이면 사용 불가
# 해결책: 새 이벤트 루프를 만들고, 스레드에서 run_until_complete로 async 함수 실행
# 클라이언트(get_client())는 앱 시작 시 한 번만 초기화하고 재사용
if st.button("질문하기"):
    if query.strip():
        with st.spinner("LLM 응답 생성 중..."):

            def run_async_task(coro):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(coro)

            result = run_async_task(ask_llm(query))

            st.subheader("LLM 응답:")
            st.write(result)
    else:
        st.warning("질문을 입력해주세요.")
