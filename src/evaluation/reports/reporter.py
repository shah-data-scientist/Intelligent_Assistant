"""Report generation for evaluation results.

Generates human-readable reports in JSON, Markdown, and HTML formats.
"""

import json
import logging
from datetime import datetime
from typing import Any

from src.evaluation.evaluators.system_evaluator import EvaluationReport

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate evaluation reports in multiple formats."""

    def generate_json(self, report: EvaluationReport) -> str:
        """Generate JSON format report.

        Args:
            report: Evaluation report

        Returns:
            JSON string
        """
        return json.dumps(report.model_dump(), indent=2, ensure_ascii=False)

    def generate_markdown(self, report: EvaluationReport) -> str:
        """Generate Markdown format report.

        Args:
            report: Evaluation report

        Returns:
            Markdown string
        """
        md = []

        # Header
        md.append("# RAG System Evaluation Report\n")
        md.append(f"**Date:** {report.timestamp}  ")
        md.append(f"**Dataset:** v{report.dataset_version}  ")
        md.append(f"**Total Queries:** {report.total_queries}\n")
        md.append("---\n")

        # Overall Status
        md.append("## Overall Status\n")
        status = report.overall_status
        md.append("| Metric | Value | Threshold | Status |")
        md.append("|--------|-------|-----------|--------|")

        quality_status = "✅ PASS" if status["quality_pass"] else "❌ FAIL"
        md.append(
            f"| Quality Score | {status['quality_score']:.3f} | "
            f"≥ {status['quality_sla']} | {quality_status} |"
        )

        latency_status = "✅ PASS" if status["latency_pass"] else "❌ FAIL"
        md.append(
            f"| Avg Latency | {status['avg_latency_ms']:.0f}ms | "
            f"< {status['latency_sla_ms']}ms | {latency_status} |"
        )

        overall_status_text = "✅ **PASS**" if status["overall_pass"] else "❌ **FAIL**"
        md.append(f"| **Overall** | - | - | {overall_status_text} |")
        md.append("")

        # Retrieval Performance
        md.append("## Retrieval Performance\n")
        retr = report.retrieval_metrics
        md.append("| Metric | Score |")
        md.append("|--------|-------|")

        if retr.get("overall_hit_rate") is not None:
            md.append(f"| Hit Rate | {retr['overall_hit_rate']:.3f} |")
            md.append(f"| MRR | {retr['overall_mrr']:.3f} |")
            md.append(f"| Precision@5 | {retr.get('overall_precision@5', 0):.3f} |")
            md.append(f"| Recall@5 | {retr.get('overall_recall@5', 0):.3f} |")
            md.append(f"| F1@5 | {retr.get('overall_f1@5', 0):.3f} |")
        else:
            md.append("| *No ground truth available* | - |")
        md.append("")

        # Interpretation
        if retr.get("overall_hit_rate") is not None:
            hit_rate = retr["overall_hit_rate"]
            md.append("**Interpretation:**  ")
            md.append(f"- {hit_rate*100:.0f}% of queries retrieved at least one relevant event")

            mrr = retr["overall_mrr"]
            avg_rank = 1.0 / mrr if mrr > 0 else float('inf')
            md.append(f"- Average rank of first relevant result: {avg_rank:.1f}")

            precision = retr.get("overall_precision@5", 0)
            md.append(f"- {precision*100:.0f}% of top-5 results are relevant")
            md.append("")

        # Generation Quality
        md.append("## Generation Quality\n")
        gen = report.generation_metrics
        md.append("| Metric | Score |")
        md.append("|--------|-------|")
        md.append(f"| Faithfulness | {gen['avg_faithfulness']:.3f} |")
        md.append(f"| Relevancy | {gen['avg_relevancy']:.3f} |")
        md.append(f"| Language Consistency | {gen['language_consistency_rate']*100:.0f}% |")
        md.append(f"| **Quality Score** | **{gen['avg_quality_score']:.3f}** |")
        md.append("")

        # Interpretation
        md.append("**Interpretation:**  ")
        md.append(f"- {gen['avg_faithfulness']*100:.0f}% grounding to sources (minimal hallucination)")
        md.append(f"- {gen['avg_relevancy']*100:.0f}% relevance to user queries")
        md.append(f"- {gen['language_consistency_rate']*100:.0f}% language consistency (bilingual support)")
        md.append("")

        # Latency Analysis
        md.append("## Latency Analysis\n")
        lat = report.latency_analysis
        if lat:
            md.append("| Percentile | Latency (ms) |")
            md.append("|------------|--------------|")
            md.append(f"| Average | {lat['avg_latency_ms']:.0f} |")
            md.append(f"| Min | {lat['min_latency_ms']:.0f} |")
            md.append(f"| P50 (Median) | {lat['p50_latency_ms']:.0f} |")
            md.append(f"| P95 | {lat['p95_latency_ms']:.0f} |")
            md.append(f"| P99 | {lat['p99_latency_ms']:.0f} |")
            md.append(f"| Max | {lat['max_latency_ms']:.0f} |")
            md.append("")

            sla_compliance = lat['sla_compliance_rate'] * 100
            md.append(f"**SLA Compliance:** {sla_compliance:.0f}% of queries under 2000ms\n")

        # Query Type Breakdown
        md.append("## Query Type Breakdown\n")
        by_type = {}
        for result in report.per_query_results:
            qtype = result.get("query_type", "unknown")
            if qtype not in by_type:
                by_type[qtype] = {"count": 0, "quality_scores": [], "hit_rates": []}

            by_type[qtype]["count"] += 1

            if "quality_score" in result:
                by_type[qtype]["quality_scores"].append(result["quality_score"])
            if result.get("hit_rate") is not None:
                by_type[qtype]["hit_rates"].append(result["hit_rate"])

        md.append("| Query Type | Count | Avg Hit Rate | Avg Quality |")
        md.append("|------------|-------|--------------|-------------|")

        for qtype, data in sorted(by_type.items()):
            count = data["count"]
            avg_hit = sum(data["hit_rates"]) / len(data["hit_rates"]) if data["hit_rates"] else None
            avg_quality = sum(data["quality_scores"]) / len(data["quality_scores"]) if data["quality_scores"] else None

            hit_str = f"{avg_hit:.3f}" if avg_hit is not None else "N/A"
            quality_str = f"{avg_quality:.3f}" if avg_quality is not None else "N/A"

            md.append(f"| {qtype} | {count} | {hit_str} | {quality_str} |")
        md.append("")

        # Recommendations
        md.append("## Recommendations\n")
        recommendations = self._generate_recommendations(report)
        for rec in recommendations:
            md.append(f"- {rec}")
        md.append("")

        return "\n".join(md)

    def generate_html(self, report: EvaluationReport) -> str:
        """Generate HTML format report.

        Args:
            report: Evaluation report

        Returns:
            HTML string
        """
        # For simplicity, convert markdown to basic HTML
        md_report = self.generate_markdown(report)

        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append("<meta charset='utf-8'>")
        html.append("<title>RAG Evaluation Report</title>")
        html.append("<style>")
        html.append("body { font-family: Arial, sans-serif; max-width: 1200px; margin: 40px auto; padding: 20px; }")
        html.append("table { border-collapse: collapse; width: 100%; margin: 20px 0; }")
        html.append("th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }")
        html.append("th { background-color: #4CAF50; color: white; }")
        html.append("tr:nth-child(even) { background-color: #f2f2f2; }")
        html.append("h1 { color: #333; }")
        html.append("h2 { color: #666; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }")
        html.append(".pass { color: green; font-weight: bold; }")
        html.append(".fail { color: red; font-weight: bold; }")
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")

        # Convert markdown to HTML (basic conversion)
        for line in md_report.split("\n"):
            if line.startswith("# "):
                html.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("| "):
                # Table row
                if not html[-1].startswith("<table>") and not html[-1].startswith("<tr>"):
                    html.append("<table>")

                cells = [c.strip() for c in line.split("|")[1:-1]]
                if all(c.startswith("-") for c in cells):
                    # Skip separator row
                    continue

                row_html = "<tr>"
                for cell in cells:
                    cell_clean = cell.replace("✅", "<span class='pass'>✅</span>")
                    cell_clean = cell_clean.replace("❌", "<span class='fail'>❌</span>")

                    if line.startswith("| Metric | ") or line.startswith("| Query Type | "):
                        row_html += f"<th>{cell_clean}</th>"
                    else:
                        row_html += f"<td>{cell_clean}</td>"
                row_html += "</tr>"
                html.append(row_html)
            elif html[-1].startswith("<tr>") and not line.startswith("| "):
                # End table
                html.append("</table>")
                html.append(f"<p>{line}</p>")
            elif line.startswith("- "):
                html.append(f"<li>{line[2:]}</li>")
            elif line == "":
                continue
            else:
                html.append(f"<p>{line}</p>")

        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)

    def _generate_recommendations(self, report: EvaluationReport) -> list[str]:
        """Generate actionable recommendations based on report.

        Args:
            report: Evaluation report

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check retrieval metrics
        retr = report.retrieval_metrics
        if retr.get("overall_hit_rate") is not None:
            if retr["overall_hit_rate"] < 0.7:
                recommendations.append(
                    f"**Low Hit Rate ({retr['overall_hit_rate']:.2f})**: "
                    "Consider improving retrieval by adjusting query refinement or expanding the index."
                )

            if retr["overall_mrr"] < 0.5:
                recommendations.append(
                    f"**Low MRR ({retr['overall_mrr']:.2f})**: "
                    "Relevant results are ranked too low. Review ranking algorithm or metadata filtering."
                )

        # Check generation metrics
        gen = report.generation_metrics
        if gen["avg_faithfulness"] < 0.8:
            recommendations.append(
                f"**Low Faithfulness ({gen['avg_faithfulness']:.2f})**: "
                "High hallucination risk. Review RAG prompts and grounding instructions."
            )

        if gen["avg_relevancy"] < 0.7:
            recommendations.append(
                f"**Low Relevancy ({gen['avg_relevancy']:.2f})**: "
                "Answers not addressing queries well. Review generation prompts and retrieval quality."
            )

        # Check latency
        lat = report.latency_analysis
        if lat and lat["avg_latency_ms"] > report.overall_status["latency_sla_ms"]:
            recommendations.append(
                f"**High Latency ({lat['avg_latency_ms']:.0f}ms)**: "
                "Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching."
            )

        # Check query type performance
        by_type = {}
        for result in report.per_query_results:
            qtype = result.get("query_type", "unknown")
            if qtype not in by_type:
                by_type[qtype] = []
            if "quality_score" in result:
                by_type[qtype].append(result["quality_score"])

        for qtype, scores in by_type.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score < 0.7:
                    recommendations.append(
                        f"**Low Performance on '{qtype}' queries ({avg_score:.2f})**: "
                        f"Consider adding more training examples or specific handling for this query type."
                    )

        if not recommendations:
            recommendations.append("**System performing well!** All metrics meet or exceed SLAs.")

        return recommendations

    def save_report(
        self,
        report: EvaluationReport,
        output_path: str,
        format: str = "markdown"
    ) -> None:
        """Save report to file.

        Args:
            report: Evaluation report
            output_path: Path to save report
            format: Report format ("json", "markdown", "html")
        """
        if format == "json":
            content = self.generate_json(report)
        elif format == "markdown":
            content = self.generate_markdown(report)
        elif format == "html":
            content = self.generate_html(report)
        else:
            raise ValueError(f"Unknown format: {format}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Saved {format} report to: {output_path}")
