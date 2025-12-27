from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class AiAssistant(models.Model):
    _name = "ai.assistant"
    _description = "AI Assistant Session"
    _order = "create_date desc"

    name = fields.Char(string="Session Name", required=True, default="New AI Session")
    user_id = fields.Many2one(
        "res.users", 
        string="User", 
        required=True, 
        default=lambda self: self.env.user
    )
    message_ids = fields.One2many(
        "ai.message", 
        "assistant_id", 
        string="Messages",
        copy=False
    )
    active = fields.Boolean(default=True)
    create_date = fields.Datetime(string="Created On")
    write_date = fields.Datetime(string="Last Updated")

    def call_external_llm(self, question, context=""):
        """
        Calls external LLM (OpenAI, Claude, etc.) with proper error handling.
        """
        # Get configuration from system parameters
        api_key = self.env["ir.config_parameter"].sudo().get_param("ai_assistant.api_key")
        endpoint = self.env["ir.config_parameter"].sudo().get_param("ai_assistant.endpoint")
        
        # Check if configuration exists
        if not api_key or api_key.strip() == "":
            raise UserError(
                "⚠️ API Key not configured. "
                "Please set your AI API key in Settings → Technical → Parameters → System Parameters.\n"
                "Create a parameter with key: 'ai_assistant.api_key'"
            )
        
        if not endpoint or endpoint.strip() == "":
            endpoint = "https://api.openai.com/v1/chat/completions"
            self.env["ir.config_parameter"].sudo().set_param("ai_assistant.endpoint", endpoint)

        _logger.info(f"Calling LLM API: {endpoint}")

        # Prepare the request
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        
        # Prepare the conversation with context
        messages = []
        
        # Add system message with context
        if context:
            system_message = f"""You are an AI assistant integrated with Odoo CRM. 
            You have access to the following record context:
            
            {context}
            
            Please use this context to answer questions about the record.
            Be helpful, concise, and professional."""
            messages.append({"role": "system", "content": system_message})
        
        # Add user question
        messages.append({"role": "user", "content": question})
        
        payload = {
            "model": "gpt-3.5-turbo",  # or "gpt-4" if available
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        try:
            # Make the API call
            response = requests.post(
                endpoint, 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            
            # Extract the answer
            if "choices" in response_data and len(response_data["choices"]) > 0:
                answer = response_data["choices"][0]["message"]["content"]
                _logger.info(f"LLM Response received: {len(answer)} characters")
                return answer.strip()
            else:
                _logger.error(f"Unexpected API response: {response_data}")
                raise UserError("⚠️ The AI service returned an unexpected response format.")
                
        except requests.exceptions.ConnectionError:
            raise UserError("🔌 Connection Error: Cannot connect to AI service. Check your internet connection.")
        except requests.exceptions.Timeout:
            raise UserError("⏱️ Timeout Error: The AI service took too long to respond.")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise UserError("🔑 Authentication Error: Invalid API key. Please check your API key in settings.")
            elif response.status_code == 429:
                raise UserError("💳 Rate Limit Error: You've exceeded your API quota. Please check your account limits.")
            else:
                error_msg = f"HTTP Error {response.status_code}: {response.text}"
                _logger.error(error_msg)
                raise UserError(f"🌐 API Error {response.status_code}: Please check your API configuration.")
        except json.JSONDecodeError:
            raise UserError("📄 Invalid Response: The AI service returned invalid JSON.")
        except Exception as e:
            _logger.error(f"Unexpected error in LLM call: {str(e)}", exc_info=True)
            raise UserError(f"❌ Unexpected Error: {str(e)}")

    def action_test_llm(self):
        """
        Test action triggered by button - uses a sample question.
        """
        self.ensure_one()
        
        test_question = "What is Odoo and how can it help with CRM?"
        test_context = "Testing the AI Assistant integration with Odoo CRM."
        
        try:
            answer = self.call_external_llm(test_question, test_context)
            
            # Show result in notification
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "✅ AI Test Successful",
                    "message": f"AI Response: {answer[:200]}...",
                    "type": "success",
                    "sticky": False,
                }
            }
        except UserError as e:
            # Re-raise UserError to show in UI
            raise e
        except Exception as e:
            raise UserError(f"Test failed: {str(e)}")

    def action_clear_history(self):
        """
        Clear all messages for this assistant.
        """
        self.ensure_one()
        self.message_ids.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "🗑️ History Cleared",
                "message": "All conversation history has been cleared.",
                "type": "info",
                "sticky": False,
            }
        }

    def _cron_cleanup_old_sessions(self):
        """
        Cron job to cleanup old inactive sessions.
        """
        days_old = 30
        old_date = fields.Datetime.subtract(fields.Datetime.now(), days=days_old)
        
        old_sessions = self.search([
            ("write_date", "<", old_date),
            ("active", "=", True)
        ])
        
        count = len(old_sessions)
        old_sessions.write({"active": False})
        
        _logger.info(f"Cleaned up {count} old AI sessions older than {days_old} days.")

class AiMessage(models.Model):
    _name = "ai.message"
    _description = "AI Conversation Message"
    _order = "timestamp asc"

    assistant_id = fields.Many2one(
        "ai.assistant", 
        string="Assistant", 
        required=True, 
        ondelete="cascade"
    )
    question = fields.Text(string="User Question", required=True)
    answer = fields.Text(string="AI Response", required=True)
    timestamp = fields.Datetime(
        string="Time", 
        default=lambda self: fields.Datetime.now(),
        required=True
    )
    model_context = fields.Char(string="Source Model")
    record_id = fields.Integer(string="Record ID")
    
    def name_get(self):
        result = []
        for message in self:
            timestamp = fields.Datetime.context_timestamp(
                self, 
                message.timestamp
            ).strftime("%Y-%m-%d %H:%M")
            name = f"{timestamp}: {message.question[:50]}..."
            result.append((message.id, name))
        return result