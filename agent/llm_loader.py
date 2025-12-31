import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.llms import LlamaCpp
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

load_dotenv()

PHI_MODEL_PATH = "llm_models/phi-3-mini-4k-instruct-q4.gguf"
QWEN_MODEL_PATH = "llm_models/qwen2.5-3b-instruct-q4_k_m.gguf"



# SERVER-LEVEL CACHE (ONE-TIME LOAD)

@st.cache_resource(show_spinner=False)
def preload_local_models():
    cpu_threads = max(1, os.cpu_count() // 2)

    models = {}
    system_status = {
        "phi_loaded": False,
        "qwen_loaded": False,
        "phi_error": None,
        "qwen_error": None,
    }

 
    # PHI MODEL

    with st.spinner(" Loading Phi-3 Mini Model..."):
        try:
            phi = LlamaCpp(
                model_path=PHI_MODEL_PATH,
                n_ctx=1024,
                n_batch=128,
                n_threads=cpu_threads,
                temperature=0.2,
                top_p=0.9,
                repeat_penalty=1.1,
                verbose=False,
            )

            phi.invoke("""
                You are a travel intent extractor.
                Extract travel details from:
                "Plan a trip to Goa from Delhi for 5 days with 2 people."
                Return JSON only.
                """)
            models["phi"] = {
                "instance": phi,
                "provider": "Local",
                "model_name": "phi-3-mini-4k-q4",
                "status": "loaded",
            }
            system_status["phi_loaded"] = True

        except Exception as e:
            system_status["phi_error"] = str(e)

    # QWEN MODEL

    with st.spinner(" Loading Qwen 2.5 Model..."):
        try:
            qwen = LlamaCpp(
                model_path=QWEN_MODEL_PATH,
                n_ctx=768,
                n_batch=128,
                n_threads=cpu_threads,
                temperature=0.15,
                top_p=0.85,
                repeat_penalty=1.05,
                verbose=False,
            )

            qwen.invoke("""
                You are a travel intent extractor.
                Extract travel details from:
                "Plan a trip to Goa from Delhi for 5 days with 2 people."
                Return JSON only.
                """)
            models["qwen"] = {
                "instance": qwen,
                "provider": "Local",
                "model_name": "qwen2.5-3b-q4",
                "status": "loaded",
            }
            system_status["qwen_loaded"] = True

        except Exception as e:
            system_status["qwen_error"] = str(e)

        return {
            "models": models,
            "system_status": system_status
        }



# MAIN LOADER

def load_llm(force_local: bool = False, local_model_choice: str | None = None):
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

 
    # Try HuggingFace API
 
    if not force_local and hf_token:
        try:
            endpoint = HuggingFaceEndpoint(
                repo_id="mistralai/Mistral-7B-Instruct-v0.2",
                task="conversational",
                huggingfacehub_api_token=hf_token,
                temperature=0.2,
                max_new_tokens=512,
            )

            return {
                "instance": ChatHuggingFace(llm=endpoint),
                "provider": "HuggingFace",
                "model_name": "mistralai/Mistral-7B-Instruct-v0.2",
                "status": "connected",
            }

        except Exception:
            pass  

 
    # LOCAL FALLBACK

    preload = preload_local_models()
    models = preload["models"]

    choice = local_model_choice or "phi"

    if choice not in models:
        raise RuntimeError("No usable local model found")

    return models[choice]



