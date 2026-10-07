import os
from google import genai
from google.genai import types
from django.conf import settings
from .models import AIConversation, AIMessage
import json

class GeminiAIService:
    def __init__(self):
        # We need the API key from settings. If not present, we will fallback gracefully or throw an error.
        self.api_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def handle_conversation_step(self, conversation, user_message=None):
        if user_message:
            # Save user message
            AIMessage.objects.create(
                conversation=conversation,
                role='user',
                content=user_message
            )
        
        # Determine next step and what to ask
        if conversation.step == 'industry':
            if user_message:
                conversation.extracted_data['industry'] = user_message
                conversation.step = 'description'
                conversation.step_index = 2
                conversation.save()
                return self._ask_description(conversation)
            else:
                return self._ask_industry(conversation)
                
        elif conversation.step == 'description':
            conversation.extracted_data['description'] = user_message
            conversation.step = 'funding'
            conversation.step_index = 3
            conversation.save()
            return self._ask_funding(conversation)
            
        elif conversation.step == 'funding':
            conversation.extracted_data['funding_goal'] = user_message
            conversation.step = 'done'
            conversation.step_index = 4
            
            # Here we call Gemini to generate the draft blueprint based on extracted_data
            draft = self._generate_draft_with_gemini(conversation)
            conversation.extracted_data['draft'] = draft
            conversation.save()
            
            return self._finalize_blueprint(conversation)

    def _ask_industry(self, conversation):
        msg = AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content="Hi, I'm Damini Advisor. I can help you create a new project. To get started, what industry is your project in?",
            suggestions=["Technology", "Clean Energy", "Real Estate", "Healthcare", "Fintech"]
        )
        return msg

    def _ask_description(self, conversation):
        ind = conversation.extracted_data.get('industry', 'your industry')
        msg = AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=f"Great! You chose {ind}. Now, could you provide a brief description of your business idea?",
            suggestions=["A renewable energy solar farm project", "A downtown tech hub", "An innovative healthcare app"]
        )
        return msg

    def _ask_funding(self, conversation):
        msg = AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content="Perfect. What is your overall funding goal for this project?",
            suggestions=["100000", "500000", "1000000", "5000000"]
        )
        return msg

    def _finalize_blueprint(self, conversation):
        msg = AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content="I've generated a complete project blueprint based on our conversation. Review it below!",
            suggestions=["Apply to Project"]
        )
        return msg

    def _generate_draft_with_gemini(self, conversation):
        data = conversation.extracted_data
        prompt = f"""
        Generate a business project draft based on these inputs:
        Industry: {data.get('industry')}
        Description: {data.get('description')}
        Funding Goal: {data.get('funding_goal')}
        
        Output a JSON object with EXACTLY these keys:
        title, short_description, full_description, funding_goal, minimum_investment, target_roi, 
        industry_name, country, location, funding_stage, timeline_months, current_status, 
        next_milestones, use_of_funds, skin_in_the_game, minimum_contribution, expected_roi, 
        potential_monthly_revenue, hold_period_months, timeline_to_operations_months, 
        team_members_text, confidentiality_agreement_text
        """
        
        if not self.client:
            # Fallback mock if no API key
            return {
                "title": f"AI Project: {data.get('industry')} Innovation",
                "short_description": "AI-assisted business opportunity...",
                "full_description": data.get('description'),
                "funding_goal": data.get('funding_goal', "0"),
                "minimum_investment": "1000",
                "target_roi": "15",
                "industry_name": data.get('industry'),
                "country": "United States",
                "location": "Global",
                "funding_stage": "Seed",
                "timeline_months": 36,
                "current_status": "Ready for investment pipeline",
                "next_milestones": "Q1: Prototype & MVP\nQ2: Pilot Customers",
                "use_of_funds": "40% R&D, 30% Sales & Marketing",
                "skin_in_the_game": "100000",
                "minimum_contribution": "1000",
                "expected_roi": "15",
                "potential_monthly_revenue": "45000",
                "hold_period_months": 36,
                "timeline_to_operations_months": 1,
                "team_members_text": "Alex Vance (CEO)",
                "confidentiality_agreement_text": "Standard NDA required."
            }

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print("Gemini Error:", e)
            return {}
