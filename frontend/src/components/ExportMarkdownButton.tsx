import type { ReviewResponse } from "../types/review";
import { buildReportFilename, exportReviewMarkdown } from "../lib/exportMarkdown";

interface ExportMarkdownButtonProps {
  result: ReviewResponse | null;
  title?: string | null;
}

export function ExportMarkdownButton({
  result,
  title,
}: ExportMarkdownButtonProps) {
  const handleExport = () => {
    if (!result) {
      return;
    }
    const markdown = exportReviewMarkdown(result, title);
    const blob = new Blob([markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = buildReportFilename(title);
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <button
      type="button"
      className="button button--secondary"
      onClick={handleExport}
      disabled={!result}
    >
      Export Markdown
    </button>
  );
}
