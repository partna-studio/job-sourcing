from digistudio.utils.lchain import get_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, field_validator


def studio_agent(model_name, prompt_path, pyParser, inputs):
    llm = get_model(model_name)
    with open(prompt_path, "r") as f: template = f.read()
    parser = PydanticOutputParser(pydantic_object=pyParser)
    prompt = ChatPromptTemplate.from_template( template + "\n{format_instructions}", partial_variables={"format_instructions": parser.get_format_instructions()})
    chain = prompt | llm | parser
    response = chain.invoke(inputs)
    return response

class JobMatchResponse(BaseModel):
    # Field descriptions help the AI understand what to put in each key
    score: float = Field(
        ..., 
        description="A match score between 0.00 and 7.00 based on the resume and job description."
    )
    rationale: str = Field(
        ..., 
        description="A concise explanation of why this specific score was awarded."
    )

    # This validator ensures the AI stays within your 0-7 boundary
    @field_validator('score')
    def score_within_range(cls, v):
        if not 0 <= v <= 7:
            raise ValueError('Score must be between 0 and 7')
        return round(v, 2)
    
def job_matching_agent(jobs, resume):
    model_name = 'mistralai/mistral-medium-3-instruct'
    prompt_path = "text/prompt.txt" 
    pyParser = JobMatchResponse
    for job in jobs:
        inputs = {"resume": resume, "job_title": job['general_info']['employmentTitle'],"job_description": job['general_info']['description']}
        response = studio_agent(model_name, prompt_path, pyParser, inputs)
        job['stats'] = response.model_dump()
    return jobs