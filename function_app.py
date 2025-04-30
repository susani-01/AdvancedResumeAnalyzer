
import azure.functions as func
import logging
import os
import pyodbc
import json
import datetime
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import openai
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, MetaData, insert

load_dotenv()

app = func.FunctionApp()

@app.route(route="process_resume", auth_level=func.AuthLevel.ANONYMOUS)
def process_resume(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing resume upload via HTTP.')

    try:
        file = req.files.get('file')
        if not file:
            return func.HttpResponse("No file uploaded.", status_code=400)

        form_recognizer = DocumentAnalysisClient(
            endpoint=os.environ["FORM_RECOGNIZER_ENDPOINT"],
            credential=AzureKeyCredential(os.environ["FORM_RECOGNIZER_KEY"])
        )
        poller = form_recognizer.begin_analyze_document("prebuilt-document", file.stream.read())
        result = poller.result()
        resume_text = resume_text = "\n".join([
            line.content 
            for page in result.pages 
            for line in page.lines  
        ])

        api_key=os.getenv("OPENAI_API_KEY")
        response = openai.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": """
                    Analyze this resume and return JSON with:
                    - score (0-100)
                    - skills_match (list)
                    - missing_skills (list)
                    - suggested_improvements
                """},
                {"role": "user", "content": resume_text}
            ],
            #response_format={ "type": "json_object" }
        )
        analysis = json.loads(response.choices[0].message.content)

        
       
        
        # Build connection string using SQLAlchemy's format
        conn_str = f"mssql+pyodbc://sqladmin:{os.environ['SQL_PASSWORD']}@{os.environ['SQL_SERVER']}.database.windows.net/ResumeDB?driver=ODBC+Driver+17+for+SQL+Server"
        engine = create_engine(conn_str)

        # Reflect the existing table
        metadata = MetaData()
        resume_analyses = Table('ResumeAnalyses', metadata, autoload_with=engine)

        # Insert values
        with engine.begin() as conn:
            stmt = insert(resume_analyses).values(
                FileName=file.filename,
                ResumeText=resume_text[:8000],
                Score=analysis.get("score"),
                SkillsMatch=", ".join(analysis.get("skills_match", [])),
                MissingSkills=", ".join(analysis.get("missing_skills", [])),
                Suggestions=analysis.get("suggested_improvements"),
                JSONAnalysis=json.dumps(analysis)
            )
            conn.execute(stmt)
            conn.commit()

        return func.HttpResponse(json.dumps(analysis), mimetype="application/json")

    except Exception as e:
        logging.error(f"Error processing resume: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
