from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from cv_json_gemini import cv_json
# import cv_json
from spire.doc import *
from spire.doc.common import *
import json
 
app = FastAPI()


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()
        if not (filename.endswith(".pdf") or filename.endswith(".doc") or filename.endswith(".docx")):
            raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")

        file_path = os.path.join(file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extracted_json = await cv_json(file_path)

        if not extracted_json:
            raise HTTPException(status_code=500, detail="Failed to extract data. JSON response is empty.")
        
        print("extracted_json:", extracted_json)
        json_dict = json.loads(extracted_json)
        return  json_dict

        
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))