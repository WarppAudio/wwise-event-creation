"""Event/object name formatting: prefixes, wildcards, letter case, loop suffixes."""
import re

# Characters allowed in naming prefixes/suffixes typed in Settings.
ALLOWED_PATTERN = re.compile(r'^[A-Za-z0-9_\$,\s]+$')

# Characters Wwise does not accept in object names.
FORBIDDEN_NAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def is_valid_object_name(name: str) -> bool:
    return bool(name) and not FORBIDDEN_NAME_CHARS.search(name) and name == name.strip()


def format_event_name(name: str, prefix: str, settings_manager, parent_workunit: str = None) -> str:
    """
    Format the event name by applying a prefix, handling wildcards, and adjusting letter casing.
    Wildcard $parent in prefix will be replaced by parent_workunit if provided.
    """
    had_parent_wildcard = '$parent' in prefix
    if parent_workunit and had_parent_wildcard:
        prefix = prefix.replace('$parent', parent_workunit)

    # "Inherit name from parent": append the parent work unit / folder name to
    # the prefix, unless the $parent wildcard already placed it explicitly.
    if (parent_workunit and not had_parent_wildcard
            and settings_manager.get('INHERIT_NAME_FROM_PARENT', False)):
        prefix = f"{prefix}_{parent_workunit}" if prefix else parent_workunit

    # Normalize separators
    prefix = re.sub(r'[\s,]+', '_', prefix).strip('_')
    prefix = re.sub(r'__+', '_', prefix)

    words_not_capital = settings_manager.get('WORDS_NOT_CAPITALIZE', [])
    letter_case_event_name = settings_manager.get('LETTER_CASE_EVENT_NAME', None)
    loop_naming = settings_manager.get('NAMING_FOR_LOOPS', '')

    # Prepare patterns for words to skip capitalization
    direct_words = []
    regex_words = []
    for item in words_not_capital:
        item_strip = item.strip()
        if '#' in item_strip:
            pattern = '^' + item_strip.replace('#', r'\d+') + '$'
            try:
                regex_words.append(re.compile(pattern))
            except re.error:
                continue
        else:
            direct_words.append(item_strip)

    base_name = name.replace(' ', '_').replace('-', '_')
    base_name = re.sub(r'__+', '_', base_name)

    words = base_name.strip('_').split('_')
    formatted_words = []

    for word in words:
        skip_capitalization = False
        if word in direct_words or word == loop_naming:
            skip_capitalization = True
        else:
            for rgx in regex_words:
                if rgx.match(word):
                    skip_capitalization = True
                    break

        if skip_capitalization:
            formatted_words.append(word)
        else:
            if letter_case_event_name == 'upper':
                formatted_words.append(word.capitalize())
            elif letter_case_event_name == 'lower':
                formatted_words.append(word.lower())
            else:
                formatted_words.append(word)

    formatted_base = '_'.join(formatted_words)

    if prefix and not prefix.endswith('_'):
        prefix += '_'

    return f"{prefix}{formatted_base}".strip('_')


def _segment_pattern(token: str):
    """Match 'token' only as a whole segment of a name: bounded by the start or
    end of the name, an underscore, or a dash. Loop detection and loop keyword
    removal both use it, so they always agree on what counts as a keyword."""
    return re.compile(r'(?:^|(?<=[_-]))' + re.escape(token) + r'(?=[_-]|$)')


def check_if_is_loop_sound(sound_name: str, tokens: list) -> bool:
    """
    Checks if 'sound_name' contains any of the given 'tokens' in a case-sensitive manner.
    A token must be preceded by start-of-string, underscore, or dash,
    and followed by underscore, dash, or end-of-string.
    """
    for token in tokens:
        token = token.strip()
        if token and _segment_pattern(token).search(sound_name):
            return True
    return False


def clean_object_name(raw_name: str, words_remove: list, loop_tokens: list, loop_suffix: str):
    """
    Strip configured words from a source object name and normalize loop naming.
    Returns (cleaned_name, is_loop).
    """
    name = raw_name
    for w in words_remove:
        name = name.replace(w, "")
    name = re.sub(r"_+", "_", name).strip("_")

    is_loop = check_if_is_loop_sound(name, loop_tokens)
    if is_loop:
        # Drop loop keywords (and a suffix that is already there) as whole
        # segments only, so "lp" is not cut out of "Alpha" or "help".
        for t in [*loop_tokens, loop_suffix]:
            t = t.strip()
            if t:
                name = _segment_pattern(t).sub("", name)
        name = re.sub(r"_+", "_", name).strip("_")
        name = f"{name}_{loop_suffix}".strip("_")
    return name, is_loop
