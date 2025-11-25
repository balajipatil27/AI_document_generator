import requests
import json
import random

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_name = "gemini-2.0-flash-exp"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        self.use_fallback = False
    
    def generate_content(self, prompt, context=None):
        if self.use_fallback:
            return self._generate_fallback_content(prompt, context)
        
        try:
            if context:
                full_prompt = f"Context: {context}\n\nTask: {prompt}\n\nPlease generate concise, focused content that fits on one page/slide (150-200 words maximum). Use clear, professional language suitable for business documents."
            else:
                full_prompt = prompt
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": full_prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 500,  # Reduced for concise content
                }
            }
            
            url = f"{self.base_url}?key={self.api_key}"
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    return self._generate_fallback_content(prompt, context)
            else:
                print(f"API Error: {response.status_code}")
                if response.status_code in [400, 401, 403, 404]:
                    self.use_fallback = True
                return self._generate_fallback_content(prompt, context)
                
        except Exception as e:
            print(f"Error generating content: {e}")
            return self._generate_fallback_content(prompt, context)
    
    def refine_content(self, content, refinement_prompt):
        if self.use_fallback:
            return self._generate_fallback_refinement(content, refinement_prompt)
        
        try:
            prompt = f"""
            Original content: {content}
            
            Refinement request: {refinement_prompt}
            
            Please refine the content above according to the refinement request. 
            Keep the content concise and focused (150-200 words maximum).
            Return only the refined content without any additional explanations.
            """
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 500,
                }
            }
            
            url = f"{self.base_url}?key={self.api_key}"
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    return self._generate_fallback_refinement(content, refinement_prompt)
            else:
                if response.status_code in [400, 401, 403, 404]:
                    self.use_fallback = True
                return self._generate_fallback_refinement(content, refinement_prompt)
                
        except Exception as e:
            return self._generate_fallback_refinement(content, refinement_prompt)
    
    def generate_outline(self, topic, doc_type):
        if self.use_fallback:
            return self._generate_fallback_outline(topic, doc_type)
        
        try:
            if doc_type == 'docx':
                prompt = f"""Generate a concise outline for a document about: {topic}
                
                Return ONLY a valid JSON array of 4-6 section headers maximum. Example format:
                ["Introduction", "Background", "Analysis", "Conclusion"]
                
                Make the sections relevant to the topic: {topic}"""
            else:
                prompt = f"""Generate slide titles for a presentation about: {topic}
                
                Return ONLY a valid JSON array of 5-7 slide titles maximum. Example format:
                ["Title Slide", "Introduction", "Key Findings", "Analysis", "Conclusion"]
                
                Make the slide titles relevant to the topic: {topic}"""
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 300,
                }
            }
            
            url = f"{self.base_url}?key={self.api_key}"
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    outline_text = result['candidates'][0]['content']['parts'][0]['text']
                    outline_text = outline_text.strip().strip('`').replace('json\n', '').replace('```', '')
                    return outline_text
                else:
                    return self._generate_fallback_outline(topic, doc_type)
            else:
                if response.status_code in [400, 401, 403, 404]:
                    self.use_fallback = True
                return self._generate_fallback_outline(topic, doc_type)
                    
        except Exception as e:
            return self._generate_fallback_outline(topic, doc_type)
    
    def _generate_fallback_content(self, prompt, context=None):
        """Generate concise sample content"""
        section_name = "this section"
        if "section:" in prompt.lower():
            try:
                section_name = prompt.split("section:")[1].split("'")[1] if "'" in prompt else "this section"
            except:
                pass
        
        # Concise content templates (150-200 words)
        content_templates = [
            f"""This {section_name} provides a focused analysis of {context or 'the topic'}. Key aspects include fundamental concepts, current trends, and practical applications.

The content is structured to deliver clear insights and actionable information suitable for business documentation.""",
            
            f"""In this {section_name}, we examine core concepts related to {context or 'this subject'}. The discussion covers essential information, relevant examples, and practical implications.

This concise analysis provides a balanced perspective on the subject matter.""",
            
            f"""This segment explores fundamental aspects of {context or 'the main topic'}. It presents key information organized for easy understanding and practical application.

The analysis is based on careful consideration of available information and expert perspectives."""
        ]
        
        section_lower = section_name.lower()
        if "introduction" in section_lower:
            return f"""Introduction to {context or 'the Topic'}

This document provides a focused overview of {context or 'the chosen subject'}. The introduction establishes context, defines key terms, and outlines the document structure.

Key objectives include providing background information, establishing relevance, and previewing main sections. This analysis aims to deliver valuable insights for informed decision-making."""
        
        elif "conclusion" in section_lower:
            return f"""Conclusion and Recommendations

Based on the analysis presented, key conclusions regarding {context or 'the subject matter'} include identified opportunities, current challenges, and strategic recommendations.

Main findings suggest potential for improvement and optimization. Recommendations focus on implementation strategies and success measurement."""
        
        elif "background" in section_lower:
            return f"""Background and Context

Understanding {context or 'this field'} requires examining historical development and current conditions. This section provides essential foundation information.

Key aspects include major developments, influential factors, current trends, and existing frameworks. This background establishes necessary context for subsequent analysis."""
        
        else:
            return random.choice(content_templates)
    
    def _generate_fallback_refinement(self, content, refinement_prompt):
        refinement = refinement_prompt.lower()
        
        if "shorten" in refinement:
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            if len(sentences) > 2:
                return '. '.join(sentences[:2]) + '.'
            return content
        
        elif "bullet" in refinement:
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            bullet_points = [f"• {sentence}" for sentence in sentences[:4] if sentence]
            return '\n'.join(bullet_points)
        
        elif "formal" in refinement:
            return content + " This refined content maintains professional standards suitable for business documentation."
        
        else:
            return content
    
    def _generate_fallback_outline(self, topic, doc_type):
        if doc_type == 'docx':
            outline = ['Introduction', 'Background', 'Analysis', 'Recommendations', 'Conclusion']
        else:
            outline = ['Title Slide', 'Introduction', 'Key Points', 'Analysis', 'Recommendations', 'Conclusion']
        
        return json.dumps(outline)