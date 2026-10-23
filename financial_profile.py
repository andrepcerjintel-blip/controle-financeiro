"""User-declared financial planning data, independent of bank originals."""
DEFAULT_PROFILE = {
    'monthly_income_cents': 0, 'essential_budget_cents': 0,
    'discretionary_budget_cents': 0, 'monthly_saving_goal_cents': 0,
    'reserve_cents': 0, 'reserve_months': 6,
    'debt_balance_cents': 0, 'debt_payment_cents': 0,
    'goal_name': '', 'goal_target_cents': 0, 'goal_saved_cents': 0,
    'goal_months': 12,
}


def validate_profile(data):
    if not isinstance(data, dict): raise ValueError('Perfil inválido')
    result = dict(DEFAULT_PROFILE)
    if set(data) - set(result): raise ValueError('Campo de perfil desconhecido')
    for key, value in data.items():
        if key == 'goal_name':
            if not isinstance(value, str) or len(value) > 120: raise ValueError('Nome da meta inválido')
            result[key] = value.strip()
        else:
            maximum = 120 if key in ('reserve_months','goal_months') else 100_000_000_000
            minimum = 1 if key in ('reserve_months','goal_months') else 0
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError('Valor inválido: ' + key)
            result[key] = value
    return result
