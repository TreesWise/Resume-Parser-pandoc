import os
import base64
import fitz  # PyMuPDF
import json
import asyncio
import aiohttp  # Async HTTP for OpenAI API
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI
from io import BytesIO
from dict_file import mapping_dict
from fastapi import HTTPException
import subprocess  # Used for calling pandoc
import tempfile
import google.generativeai as genai

load_dotenv()

async def cv_json(file_path):

    with open("output_json.json", "r", encoding="utf-8") as file:
        json_template_str = json.load(file)
    
    prompt = f"""
    You are an expert in data extraction and JSON formatting. Your task is to extract and format resume data **exactly** as per the provided JSON template {json_template_str}. Ensure strict compliance with structure, accuracy, and completeness.
    ### **Guidelines:**
    - Extract and map City, State, Country, Zipcode, and split Address fields.
    - Ensure **all** experience entries, certificates, and visas are extracted properly.
    - Generate **only** a well-structured JSON response.
    """

    async def send_gemini_flash_request(file_path, prompt):
        print("Sending Gemini 2.0 Flash API request")
        genai.configure(api_key=os.getenv("api_key"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        with open(file_path, "rb") as file:
            document = genai.upload_file(file, display_name="Sample PDF", mime_type="application/pdf")
        try:
            response = model.generate_content([prompt, document])
            cleaned_string = response.text.strip("\njson\n").strip("\n").replace("'", '"').replace("None", "null")

            try:
                extracted_json = json.loads(cleaned_string)
                return json.dumps(extracted_json, indent=4)
            except json.JSONDecodeError as e:
                print("Error parsing JSON:", e)
        except Exception as e:
            print(f"API Request Error: {e}")
            return None

    def doc_to_pdf(file_path):
        try:
            temp_dir = tempfile.mkdtemp()  
            pdf_file_path = os.path.join(temp_dir, "converted.pdf")

            # Use Pandoc for conversion
            command = f"pandoc '{file_path}' -o '{pdf_file_path}'"
            subprocess.run(command, shell=True, check=True)

            if not os.path.exists(pdf_file_path):
                raise FileNotFoundError(f"PDF conversion failed, file not found: {pdf_file_path}")

            print(f"PDF successfully created: {pdf_file_path}")
            return pdf_file_path  
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DOCX to PDF conversion failed: {str(e)}")
            
    def replace_values(data, mapping):
        if isinstance(data, dict):
            return {mapping.get(key, key): replace_values(value, mapping) for key, value in data.items()}
        elif isinstance(data, list):
            return [replace_values(item, mapping) for item in data]
        elif isinstance(data, str):
            return mapping.get(data, data)  
        return data

    async def process_images(file_path, prompt):
        print("Processing images")

        if not (file_path.endswith(".pdf") or file_path.endswith(".doc") or file_path.endswith(".docx")):
            raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")
        
        if file_path.endswith(".doc") or file_path.endswith(".docx"):
            file_path = doc_to_pdf(file_path)

        response = await send_gemini_flash_request(file_path, prompt)
        print("Response from Gemini:", response)
        updated_json = replace_values(response, mapping_dict)
        return updated_json

    return await process_images(file_path, prompt)
