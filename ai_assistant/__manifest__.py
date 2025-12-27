{
    "name": "AI Assistant Module",
    "summary": "Multi-tenant AI assistant with LLM integration.",
    "version": "1.0",
    "category": "Productivity",
    "author": "Your Company",
    "website": "https://yourwebsite.com",
    "depends": ["web"],
    "data": [
        "security/ir.model.access.csv",
        "views/ai_assistant_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ai_assistant/static/src/js/ai_widget.js",
            "ai_assistant/static/src/css/ai_widget.css",
            "ai_assistant/static/src/xml/ai_widget.xml",  # ADD THIS LINE
        ]
    },
    "demo": [],
    "application": True,
    "installable": True,
    "license": "LGPL-3",
}