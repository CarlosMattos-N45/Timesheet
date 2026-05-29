namespace Timesheet.Agent.Ui.Validation;

public static class CnpjValidator
{
    public static string OnlyDigits(string raw) => new(raw.Where(char.IsDigit).ToArray());

    public static bool IsValid(string raw)
    {
        var s = OnlyDigits(raw);
        if (s.Length != 14 || s.Distinct().Count() == 1) return false;

        int Dv(int len, int[] pesos)
        {
            int sum = 0;
            for (int i = 0; i < len; i++) sum += (s[i] - '0') * pesos[i];
            int r = sum % 11;
            return r < 2 ? 0 : 11 - r;
        }

        var d1 = Dv(12, new[] { 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2 });
        var d2 = Dv(13, new[] { 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2 });
        return d1 == s[12] - '0' && d2 == s[13] - '0';
    }
}
