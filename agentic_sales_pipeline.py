# Warning control
import warnings
warnings.filterwarnings('ignore')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import os
import yaml
import json
from datetime import datetime
from crewai import Agent, Task, Crew
os.environ['OPENAI_MODEL_NAME'] = 'gpt-4o-mini'

# Define file paths for YAML configurations
files = {
    'lead_agents': 'config/lead_qualification_agents.yaml',
    'lead_tasks': 'config/lead_qualification_tasks.yaml',
    'email_agents': 'config/email_engagement_agents.yaml',
    'email_tasks': 'config/email_engagement_tasks.yaml'
}

# Load configurations from YAML files
configs = {}
for config_type, file_path in files.items():
    with open(file_path, 'r') as file:
        configs[config_type] = yaml.safe_load(file)

# Assign loaded configurations to specific variables
lead_agents_config = configs['lead_agents']
lead_tasks_config = configs['lead_tasks']
email_agents_config = configs['email_agents']
email_tasks_config = configs['email_tasks']

from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Set, Tuple

class LeadPersonalInfo(BaseModel):
    name: str = Field(..., description="The full name of the lead.")
    job_title: str = Field(..., description="The job title of the lead.")
    role_relevance: int = Field(..., ge=0, le=10, description="A score representing how relevant the lead's role is to the decision-making process (0-10).")
    professional_background: Optional[str] = Field(..., description="A brief description of the lead's professional background.")

class CompanyInfo(BaseModel):
    company_name: str = Field(..., description="The name of the company the lead works for.")
    industry: str = Field(..., description="The industry in which the company operates.")
    company_size: int = Field(..., description="The size of the company in terms of employee count.")
    revenue: Optional[float] = Field(None, description="The annual revenue of the company, if available.")
    market_presence: int = Field(..., description="A score representing the company's market presence (0-10).")

class LeadScore(BaseModel):
    score: int = Field(..., ge=0, le=100, description="The final score assigned to the lead (0-100).")
    scoring_criteria: List[str] = Field(..., description="The criteria used to determine the lead's score.")
    validation_notes: Optional[str] = Field(None, description="Any notes regarding the validation of the lead score.")

class LeadScoringResult(BaseModel):
    personal_info: LeadPersonalInfo = Field(..., description="Personal information about the lead.")
    company_info: CompanyInfo = Field(..., description="Information about the lead's company.")
    lead_score: LeadScore = Field(..., description="The calculated score and related information for the lead.")

from crewai_tools import SerperDevTool, ScrapeWebsiteTool

# Creating Agents
lead_data_agent = Agent(
  config=lead_agents_config['lead_data_agent'],
  tools=[SerperDevTool(), ScrapeWebsiteTool()]
)

cultural_fit_agent = Agent(
  config=lead_agents_config['cultural_fit_agent'],
  tools=[SerperDevTool(), ScrapeWebsiteTool()]
)

scoring_validation_agent = Agent(
  config=lead_agents_config['scoring_validation_agent'],
  tools=[SerperDevTool(), ScrapeWebsiteTool()]
)

# Creating Tasks
lead_data_task = Task(
  config=lead_tasks_config['lead_data_collection'],
  agent=lead_data_agent
)

cultural_fit_task = Task(
  config=lead_tasks_config['cultural_fit_analysis'],
  agent=cultural_fit_agent
)

scoring_validation_task = Task(
  config=lead_tasks_config['lead_scoring_and_validation'],
  agent=scoring_validation_agent,
  context=[lead_data_task, cultural_fit_task],
  output_pydantic=LeadScoringResult
)

# Creating Crew
lead_scoring_crew = Crew(
  agents=[
    lead_data_agent,
    cultural_fit_agent,
    scoring_validation_agent
  ],
  tasks=[
    lead_data_task,
    cultural_fit_task,
    scoring_validation_task
  ],
  verbose=True
)

# Creating Agents
email_content_specialist = Agent(
  config=email_agents_config['email_content_specialist']
)

engagement_strategist = Agent(
  config=email_agents_config['engagement_strategist']
)

# Creating Tasks
email_drafting = Task(
  config=email_tasks_config['email_drafting'],
  agent=email_content_specialist
)

engagement_optimization = Task(
  config=email_tasks_config['engagement_optimization'],
  agent=engagement_strategist
)

# Creating Crew
email_writing_crew = Crew(
  agents=[
    email_content_specialist,
    engagement_strategist
  ],
  tasks=[
    email_drafting,
    engagement_optimization
  ],
  verbose=True
)

from crewai import Flow
from crewai.flow.flow import listen, start

class SalesPipeline(Flow):
    @start()
    def fetch_leads(self):
        # Pull our leads from the database
        leads = [
            {
                "lead_data": {
                    "name": "João Moura",
                    "job_title": "Director of Engineering",
                    "company": "Clearbit",
                    "email": "joao@clearbit.com",
                    "use_case": "Using AI Agent to do better data enrichment."
                },
            },
        ]
        return leads

    @listen(fetch_leads)
    def score_leads(self, leads):
        scores = lead_scoring_crew.kickoff_for_each(leads)
        self.state["score_crews_results"] = scores
        return scores

    @listen(score_leads)
    def store_leads_score(self, scores):
        # Here we would store the scores in the database
        return scores

    @listen(score_leads)
    def filter_leads(self, scores):
        return [score for score in scores if score['lead_score'].score > 70]

    @listen(filter_leads)
    def write_email(self, leads):
        scored_leads = [lead.to_dict() for lead in leads]
        emails = email_writing_crew.kickoff_for_each(scored_leads)
        return emails

    @listen(write_email)
    def send_email(self, emails):
        # Here we would send the emails to the leads
        return emails

def save_outputs_to_file(data, filename, output_dir="outputs"):
    """Save data to a file in the outputs directory"""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    
    if filename.endswith('.json'):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    elif filename.endswith('.txt'):
        with open(filepath, 'w') as f:
            f.write(str(data))
    elif filename.endswith('.csv'):
        import pandas as pd
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
        else:
            with open(filepath, 'w') as f:
                f.write(str(data))
    
    print(f"Output saved to: {filepath}")

def main():
    print("Starting Agentic Sales Pipeline...")
    
    # Create and run the flow
    flow = SalesPipeline()
    
    try:
        # Run the flow
        print("Running lead scoring and email generation...")
        emails = flow.kickoff()
        
        # Get scores from flow state
        scores = flow.state.get("score_crews_results", [])
        
        print(f"Pipeline completed successfully!")
        print(f"Generated {len(emails)} emails")
        print(f"Scored {len(scores)} leads")
        
        # Save outputs to files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save lead scoring results
        if scores:
            scoring_data = []
            for score in scores:
                try:
                    lead_data = score.pydantic
                    scoring_data.append({
                        'name': lead_data.personal_info.name,
                        'job_title': lead_data.personal_info.job_title,
                        'role_relevance': lead_data.personal_info.role_relevance,
                        'professional_background': lead_data.personal_info.professional_background,
                        'company_name': lead_data.company_info.company_name,
                        'industry': lead_data.company_info.industry,
                        'company_size': lead_data.company_info.company_size,
                        'revenue': lead_data.company_info.revenue,
                        'market_presence': lead_data.company_info.market_presence,
                        'lead_score': lead_data.lead_score.score,
                        'scoring_criteria': ', '.join(lead_data.lead_score.scoring_criteria),
                        'validation_notes': lead_data.lead_score.validation_notes
                    })
                except Exception as e:
                    print(f"Error processing score data: {e}")
                    scoring_data.append({'error': str(e)})
            
            save_outputs_to_file(scoring_data, f"lead_scoring_results_{timestamp}.csv")
        
        # Save email content
        if emails:
            email_data = []
            for i, email in enumerate(emails):
                try:
                    email_data.append({
                        'email_id': i + 1,
                        'content': email.raw,
                        'token_usage': str(email.token_usage) if hasattr(email, 'token_usage') else 'N/A'
                    })
                except Exception as e:
                    print(f"Error processing email data: {e}")
                    email_data.append({'email_id': i + 1, 'error': str(e)})
            
            save_outputs_to_file(email_data, f"generated_emails_{timestamp}.json")
        
        # Save flow summary
        summary = {
            'timestamp': timestamp,
            'total_leads_processed': len(scores) if scores else 0,
            'total_emails_generated': len(emails) if emails else 0,
            'flow_state_keys': list(flow.state.keys()) if hasattr(flow, 'state') else [],
            'status': 'completed'
        }
        
        save_outputs_to_file(summary, f"pipeline_summary_{timestamp}.json")
        
        print("\nAll outputs have been saved to the 'outputs' folder!")
        
    except Exception as e:
        print(f"Error running pipeline: {e}")
        # Save error information
        error_data = {
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'error': str(e),
            'status': 'failed'
        }
        save_outputs_to_file(error_data, f"pipeline_error_{timestamp}.json")

if __name__ == "__main__":
    main()