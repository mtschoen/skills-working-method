using UnityEngine;

public static class CombatMath
{
    public static int ApplyDamage(int health, int rawDamage, float armorFraction)
    {
        int mitigatedDamage = Mathf.RoundToInt(rawDamage * (1f - armorFraction));
        int remainingHealth = health - mitigatedDamage;
        return remainingHealth < 0 ? 0 : remainingHealth;
    }
}

public class DamageProbe : MonoBehaviour
{
    private void Start()
    {
        Debug.Log(CombatMath.ApplyDamage(100, 30, 0.25f));
    }
}
