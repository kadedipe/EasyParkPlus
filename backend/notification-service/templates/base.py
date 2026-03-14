"""
Base template engine and manager.
"""

import os
import json
import jinja2
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..core.config import settings
from ..utils.logging_utils import get_logger


class TemplateEngine:
    """
    Jinja2 template engine wrapper.
    """
    
    def __init__(self, template_dir: str):
        """
        Initialize template engine.
        
        Args:
            template_dir: Base template directory
        """
        self.template_dir = Path(template_dir)
        self.logger = get_logger(__name__)
        
        # Create Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['date'] = self._format_date
        self.env.filters['currency'] = self._format_currency
        self.env.filters['phone'] = self._format_phone
        self.env.filters['truncate'] = self._truncate
        self.env.filters['json'] = self._to_json
        
        self.logger.info(f"Template engine initialized with directory: {template_dir}")
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render template with context.
        
        Args:
            template_name: Template file name
            context: Template context
            
        Returns:
            str: Rendered template
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"Failed to render template {template_name}: {e}")
            raise
    
    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Render template from string.
        
        Args:
            template_string: Template string
            context: Template context
            
        Returns:
            str: Rendered template
        """
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"Failed to render template string: {e}")
            raise
    
    def _format_date(self, value, format="%B %d, %Y"):
        """Format date filter."""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        if isinstance(value, datetime):
            return value.strftime(format)
        return value
    
    def _format_currency(self, value, currency="USD"):
        """Format currency filter."""
        try:
            value = float(value)
            if currency == "USD":
                return f"${value:,.2f}"
            elif currency == "EUR":
                return f"€{value:,.2f}"
            elif currency == "GBP":
                return f"£{value:,.2f}"
            else:
                return f"{value:,.2f} {currency}"
        except:
            return value
    
    def _format_phone(self, value):
        """Format phone number filter."""
        import re
        cleaned = re.sub(r'\D', '', value)
        if len(cleaned) == 10:
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) == 11 and cleaned[0] == '1':
            return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        return value
    
    def _truncate(self, value, length=100, suffix="..."):
        """Truncate string filter."""
        if len(value) <= length:
            return value
        return value[:length].rsplit(' ', 1)[0] + suffix
    
    def _to_json(self, value):
        """Convert to JSON filter."""
        return json.dumps(value)


class TemplateManager:
    """
    Template manager for handling multiple template types.
    """
    
    def __init__(self):
        """Initialize template manager."""
        self.templates = {}
        self.logger = get_logger(__name__)
        
        # Initialize template engines for different types
        base_dir = Path(__file__).parent
        
        self.engines = {
            "email": TemplateEngine(str(base_dir / "email")),
            "sms": TemplateEngine(str(base_dir / "sms")),
            "push": TemplateEngine(str(base_dir / "push"))
        }
        
        self.logger.info("Template manager initialized")
    
    def render(
        self,
        template_type: str,
        template_name: str,
        context: Dict[str, Any],
        format: str = "html"
    ) -> str:
        """
        Render template by type.
        
        Args:
            template_type: Type of template (email, sms, push)
            template_name: Template name
            context: Template context
            format: Template format (html, txt, json)
            
        Returns:
            str: Rendered template
        """
        if template_type not in self.engines:
            raise ValueError(f"Unknown template type: {template_type}")
        
        # Build full template name with format
        full_name = f"{template_name}.{format}"
        
        try:
            return self.engines[template_type].render(full_name, context)
        except Exception as e:
            self.logger.error(f"Failed to render {template_type} template {full_name}: {e}")
            raise
    
    def list_templates(self, template_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List available templates.
        
        Args:
            template_type: Optional filter by type
            
        Returns:
            Dict[str, List[str]]: Available templates by type
        """
        result = {}
        
        types = [template_type] if template_type else self.engines.keys()
        
        for t in types:
            if t in self.engines:
                engine = self.engines[t]
                templates = []
                
                # Walk through template directory
                template_dir = Path(engine.template_dir)
                if template_dir.exists():
                    for file in template_dir.glob("**/*"):
                        if file.is_file():
                            rel_path = file.relative_to(template_dir)
                            templates.append(str(rel_path))
                
                result[t] = templates
        
        return result
    
    def validate_template(self, template_type: str, template_name: str, format: str = "html") -> bool:
        """
        Validate that a template exists.
        
        Args:
            template_type: Type of template
            template_name: Template name
            format: Template format
            
        Returns:
            bool: True if template exists
        """
        if template_type not in self.engines:
            return False
        
        full_name = f"{template_name}.{format}"
        template_path = Path(self.engines[template_type].template_dir) / full_name
        
        return template_path.exists()
    
    def get_template_info(self, template_type: str, template_name: str) -> Dict[str, Any]:
        """
        Get template information.
        
        Args:
            template_type: Type of template
            template_name: Template name
            
        Returns:
            Dict[str, Any]: Template info
        """
        info = {
            "type": template_type,
            "name": template_name,
            "exists": {},
            "modified": {}
        }
        
        for format in ["html", "txt", "json"]:
            full_name = f"{template_name}.{format}"
            template_path = Path(self.engines[template_type].template_dir) / full_name
            
            info["exists"][format] = template_path.exists()
            if template_path.exists():
                info["modified"][format] = datetime.fromtimestamp(
                    template_path.stat().st_mtime
                ).isoformat()
        
        return info


# Singleton instance
template_manager = TemplateManager()


def get_template_manager() -> TemplateManager:
    """
    Get template manager singleton.
    
    Returns:
        TemplateManager: Template manager instance
    """
    return template_manager