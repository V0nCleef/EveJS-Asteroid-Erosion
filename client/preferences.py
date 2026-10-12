# coding: utf-8
"""Personal visuals only; authoritative ore/radius never enter this store."""
import __builtin__ as _ae_builtins
import math as _ae_math

_AE_SETTING_KEY = 'evejsAsteroidErosionVisualsV1'
_AE_STYLES = ('dust', 'burn', 'hybrid', 'quiet')
try:
    _AE_NUMBER_TYPES = (int, long, float)
except NameError:
    _AE_NUMBER_TYPES = (int, float)
_AE_VISUAL_BOUNDS = {
    'resizeDurationMs': (0.0, 3000.0),
    'depletionDurationMs': (0.0, 2000.0),
    'dustIntensity': (0.0, 3.0),
    'dustLifetimeMs': (300.0, 4000.0),
    'dustMaxConcurrent': (1.0, 64.0),
}


def _ae_visual_values(values, defaults, strict=False):
    result = dict(defaults)
    if not isinstance(values, dict):
        if strict:
            raise ValueError('Invalid visual settings')
        return result
    for key, bounds in _AE_VISUAL_BOUNDS.items():
        if key not in values:
            continue
        value = values[key]
        try:
            valid = (isinstance(value, _AE_NUMBER_TYPES) and not isinstance(value, bool)
                     and not _ae_math.isnan(value) and not _ae_math.isinf(value)
                     and bounds[0] <= value <= bounds[1])
        except (OverflowError, TypeError, ValueError):
            valid = False
        if key == 'dustMaxConcurrent' and valid:
            valid = int(value) == value
        if not valid:
            if strict:
                raise ValueError('Invalid setting: ' + key)
            continue
        result[key] = int(value) if key != 'dustIntensity' else float(value)
    for key in ('dustEnabled', 'smoothShrink'):
        if key in values:
            if type(values[key]) is bool:
                result[key] = values[key]
            elif strict:
                raise ValueError('Invalid setting: ' + key)
    if 'depletionStyle' in values:
        if values['depletionStyle'] in _AE_STYLES:
            result['depletionStyle'] = values['depletionStyle']
        elif strict:
            raise ValueError('Invalid depletion style')
    return result


class _AEPreferences(object):
    def __init__(self, config):
        self.base = config
        self.character = None
        self.values = None

    def defaults(self):
        result = dict((key, self.base[key]) for key in _AE_VISUAL_BOUNDS)
        result.update(dustEnabled=self.base['dustEnabled'], smoothShrink=True,
                      depletionStyle='dust' if self.base['dustEnabled'] else 'quiet')
        return result

    def storage(self):
        context = globals().get('_ae_context') or {}
        session = context.get('session') or getattr(_ae_builtins, 'session', None)
        character = getattr(session, 'charid', None)
        settings = context.get('settings') or getattr(_ae_builtins, 'settings', None)
        if not character or settings is None:
            return None, None
        return character, settings.char.ui

    def snapshot(self):
        character, store = self.storage()
        defaults = self.defaults()
        if character is None:
            return defaults
        if self.character != character or self.values is None:
            try:
                saved = store.Get(_AE_SETTING_KEY, {})
            except Exception:
                # A temporarily unavailable settings service must not interrupt
                # native resize/release. Retry on the next snapshot.
                return defaults
            self.character = character
            self.values = _ae_visual_values(saved, defaults)
        return dict(self.values)

    def save(self, values):
        character, store = self.storage()
        if character is None:
            raise RuntimeError('Log in with a character before saving visual preferences')
        clean = _ae_visual_values(values, self.defaults(), strict=True)
        # Commit native storage first: failed writes cannot masquerade as saved.
        store.Set(_AE_SETTING_KEY, dict(clean))
        self.character, self.values = character, clean
        return dict(clean)

    def reset_session(self):
        self.character, self.values = None, None
