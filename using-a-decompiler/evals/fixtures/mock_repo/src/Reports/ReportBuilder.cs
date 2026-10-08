namespace Inventory.Reports;

public sealed class ReportBuilder
{
    private readonly List<string> _lines = new();

    public ReportBuilder Add(string label, decimal amount)
    {
        _lines.Add($"{label}: {amount:F2}");
        return this;
    }

    public string Build() => string.Join("\n", _lines);
}
