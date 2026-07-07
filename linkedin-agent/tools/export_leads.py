"""Export leads to an Excel (.xlsx) file for download."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from persona.core.tool import Tool, ToolResult


class ExportLeadsTool(Tool):
    name = "export_leads"
    description = (
        "Export leads from a campaign to a downloadable Excel file. "
        "Returns the download URL for the generated file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "campaign_id": {
                "type": "string",
                "description": "Campaign ID whose leads to export",
            },
            "status_filter": {
                "type": "string",
                "description": "Filter by lead status (new, contacted, replied, qualified, rejected). Leave empty for all.",
                "enum": ["new", "contacted", "replied", "qualified", "rejected"],
            },
        },
        "required": ["campaign_id"],
    }

    db: Any = None

    async def execute(self, **kwargs: Any) -> ToolResult:
        from openpyxl import Workbook

        from db.models import LeadStatus
        from db.repository import LeadRepository

        campaign_id = kwargs["campaign_id"]
        status_filter = kwargs.get("status_filter")

        if not self.db:
            return ToolResult(output=None, error="Database not configured")

        async with self.db.session() as session:
            lead_repo = LeadRepository(session)
            status = LeadStatus(status_filter) if status_filter else None
            pairs = await lead_repo.get_campaign_leads(campaign_id, status=status)

        if not pairs:
            return ToolResult(output={"count": 0, "message": "No leads found for export"})

        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Leads"

        headers = ["Name", "Title", "Company", "Location", "Headline", "Profile URL", "Status"]
        ws.append(headers)

        # Style header row
        from openpyxl.styles import Font

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for cl, lead in pairs:
            ws.append([
                lead.name,
                lead.title,
                lead.company,
                lead.location,
                lead.headline,
                lead.profile_url,
                cl.status.value,
            ])

        # Auto-fit column widths (approximate)
        for col in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in col)
            adjusted = min(max_length + 2, 50)
            ws.column_dimensions[col[0].column_letter].width = adjusted

        # Save file
        exports_dir = Path("data") / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{campaign_id[:8]}_{timestamp}.xlsx"
        filepath = exports_dir / filename
        wb.save(str(filepath))

        return ToolResult(
            output={
                "count": len(pairs),
                "filename": filename,
                "download_url": f"/v1/agent/downloads/{filename}",
                "message": f"Exported {len(pairs)} leads to {filename}",
            }
        )
