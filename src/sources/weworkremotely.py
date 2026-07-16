"""We Work Remotely — public RSS feed."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .base import Job, clean_html, get_text


def fetch(cfg: dict) -> list[Job]:
    xml = get_text("https://weworkremotely.com/remote-jobs.rss")
    root = ET.fromstring(xml)
    jobs: list[Job] = []
    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        # WWR titles look like "Company: Job Title"
        company, _, title = raw_title.partition(":")
        if not title:
            title, company = company, ""
        region = (item.findtext("region") or "").strip()
        jobs.append(
            Job(
                source="WeWorkRemotely",
                title=title.strip() or raw_title,
                company=company.strip(),
                url=(item.findtext("link") or "").strip(),
                description=clean_html(item.findtext("description")),
                location=region or "Remote",
                remote=True,
                tags=[c.text for c in item.findall("category") if c.text],
                posted="",
            )
        )
    return jobs
