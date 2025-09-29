import streamlit as st
import asyncio
from dotenv import load_dotenv
from src.fastmcp.mcp_client3 import get_gemini_client


# @st.cache_resource
# async def get_cached_client():
#     return await get_gemini_client()  # 최초 1회만 실행


# OpenAI 클라이언트 준비
async def ask_llm(user_query: str) -> str:
    client = st.session_state.client
    if client is None:
        st.error("서버에 연결하지 못했습니다.")
    return await client.chat(user_query)


async def cleanup():
    if "client" in st.session_state and st.session_state.client:
        await st.session_state.client.cleanup()
        st.session_state.pop("client", None)
    # if "loop" in st.session_state and st.session_state.loop:
    #     st.session_state.loop.stop()
    #     st.session_state.loop = None


def run_async_task(coro):
    return st.session_state.loop.run_until_complete(coro)


def run_streamlit():
    load_dotenv()

    # 페이지 레이아웃
    st.set_page_config(page_title="LLM Query Demo", layout="centered")
    st.title("FastMCP + Gemini LLM 연동 예제")
    st.write("LLM에게 질문을 보내고 답변을 받아보세요.")

    if "loop" not in st.session_state:
        st.session_state.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(st.session_state.loop)

        st.session_state.client = st.session_state.loop.run_until_complete(
            get_gemini_client()
        )
        if st.session_state.client is None:
            st.error("서버에 연결하지 못했습니다. 환경 변수를 확인하세요.")

    # 사용자 입력
    query = st.text_area("질문을 입력하세요:", height=120)

    # 버튼 클릭 시 LLM 호출
    # Streamlit 1.50.0에서는 직접 await 사용 불가
    # asyncio.run()도 이미 이벤트 루프가 실행 중이면 사용 불가
    # 해결책: 새 이벤트 루프를 만들고, 스레드에서 run_until_complete로 async 함수 실행
    # 클라이언트(get_client())는 앱 시작 시 한 번만 초기화하고 재사용
    if st.button("종료"):
        # 종료 버튼 클릭 시 cleanup 호출
        run_async_task(cleanup())

    if st.button("질문하기"):
        if query.strip():
            with st.spinner("LLM 응답 생성 중..."):

                result = run_async_task(ask_llm(query))

                st.subheader("LLM 응답:")
                st.write(result)
        else:
            st.warning("질문을 입력해주세요.")


if __name__ == "__main__":

    run_streamlit()
