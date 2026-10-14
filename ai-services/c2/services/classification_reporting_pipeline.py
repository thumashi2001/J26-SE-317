
from pathlib import Path

from services.question_classification_pipeline import (
    QuestionClassificationPipeline,
)
from services.classification_report import ClassificationReport
from services.classification_report_exporter import (
    ClassificationReportExporter,
)


DEFAULT_REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "processed"
    / "classification_reports"
    / "classification_report.json"
)


class ClassificationReportingPipeline:
    """Run classification, generate coverage, and export JSON."""

    def __init__(
        self,
        classification_pipeline=None,
        reporter=None,
        exporter=None,
    ):
        self.classification_pipeline = (
            classification_pipeline
            if classification_pipeline is not None
            else QuestionClassificationPipeline()
        )

        self.reporter = (
            reporter
            if reporter is not None
            else ClassificationReport()
        )

        self.exporter = (
            exporter
            if exporter is not None
            else ClassificationReportExporter()
        )

    def run(self, output_path=None):
        # Run the existing question classification pipeline.
        pipeline_result = self.classification_pipeline.run()

        if not isinstance(pipeline_result, dict):
            raise ValueError("Invalid classification pipeline output")

        batch_result = pipeline_result.get("batch_result")

        # Support the existing M6.4 batch result structure.
        if batch_result is None:
            if isinstance(pipeline_result.get("results"), list):
                batch_result = {
                    "results": pipeline_result["results"]
                }
            else:
                raise ValueError(
                    "Classification pipeline must expose "
                    "a list of classification results"
                )

        # Generate the coverage report.
        report = self.reporter.generate(batch_result)

        # Confirm report and pipeline summaries agree.
        pipeline_summary = pipeline_result.get("summary", {})
        report_summary = report["summary"]

        for field in (
            "total_questions",
            "classified",
            "unclassified",
            "invalid",
        ):
            if pipeline_summary.get(field) != report_summary[field]:
                raise ValueError(
                    f"Classification summary mismatch: {field}"
                )

        # Export the validated report.
        destination = (
            Path(output_path)
            if output_path is not None
            else DEFAULT_REPORT_PATH
        )

        saved_path = self.exporter.export(report, destination)

        return {
            "summary": report_summary,
            "report": report,
            "report_path": saved_path,
        }
