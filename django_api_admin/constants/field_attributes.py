"""
Django rest framework serializer fields attributes.
"""

shared_attributes = [
    'read_only', 'write_only', 'required', 'default',
    'allow_blank', 'allow_null', 'style', 'label',
    'help_text', 'initial',
]

shared_string_fields_attributes = [
    'max_length', 'min_length', 'trim_whitespace']

shared_numeric_fields_attributes = ['max_value', 'min_value']

shared_datetime_fields_attributes = ['format', 'input_formats', ]

shared_choice_fields_attributes = [
    'choices', 'allow_blank', 'html_cutoff', 'html_cutoff_text']

shared_file_fields_attributes = ['max_length', 'allow_empty_file', 'use_url']

shared_composite_fields_attributes = ['child', 'allow_empty']

shared_relationship_fields_attributes = [
    'choices', 'many', 'html_cutoff', 'html_cutoff_text',
]

field_attributes = {
    # boolean fields attributes
    'BooleanField': {*shared_attributes},

    # String fields attributes
    'CharField': [*shared_attributes, *shared_string_fields_attributes],
    'EmailField': [*shared_attributes, *shared_string_fields_attributes],
    'RegexField': [*shared_attributes, *shared_string_fields_attributes, 'regex'],
    'SlugField': [*shared_attributes, *shared_string_fields_attributes, 'allow_unicode'],
    'URLField': [*shared_attributes, *shared_string_fields_attributes],
    'UUIDField': [*shared_attributes, *shared_string_fields_attributes, 'format'],
    'IPAddressField': [*shared_attributes, *shared_string_fields_attributes, 'protocol', 'unpack_ipv4'],
    'FilePathField': [*shared_attributes, *shared_choice_fields_attributes,
                      'path', 'match', 'recursive', 'allow_files', 'allow_folders'],

    # Numeric fields
    'IntegerField': [*shared_attributes, *shared_numeric_fields_attributes],
    'FloatField': [*shared_attributes, *shared_numeric_fields_attributes],
    'DecimalField': [*shared_attributes, *shared_numeric_fields_attributes, 'max_digits', 'decimal_places',
                     'coerce_to_string', 'localize', 'rounding'],

    # Date and time fields attributes
    'DateTimeField': [*shared_attributes, *shared_datetime_fields_attributes],
    'DateField': [*shared_attributes, *shared_datetime_fields_attributes],
    'TimeField': [*shared_attributes, *shared_datetime_fields_attributes],
    'DurationField': [*shared_attributes, *shared_numeric_fields_attributes],

    # Choice fields attributes
    'ChoiceField': [*shared_attributes, *shared_choice_fields_attributes],
    'MultipleChoiceField': [*shared_attributes, *shared_choice_fields_attributes],

    # File fields attributes
    'FileField': [*shared_attributes, *shared_file_fields_attributes],
    'ImageField': [*shared_attributes, *shared_file_fields_attributes],

    # Composite fields
    'ListField': [*shared_attributes, *shared_composite_fields_attributes, 'min_length', 'max_length', ],
    'DictField': [*shared_attributes, *shared_composite_fields_attributes],
    'HStoreField': [*shared_attributes, *shared_composite_fields_attributes],
    'JSONField': [*shared_attributes, 'binary'],

    # Miscellaneous fields
    'ReadOnlyField': [*shared_attributes],
    'HiddenField': [*shared_attributes],
    'ModelField': [*shared_attributes],
    'SerializerMethodField': [*shared_attributes],

    # relationships fields
    'ManyRelatedField': [*shared_attributes, *shared_relationship_fields_attributes],
    'PrimaryKeyRelatedField': [*shared_attributes, *shared_relationship_fields_attributes],
    'HyperlinkedRelatedField': [*shared_attributes, *shared_relationship_fields_attributes],
    'SlugRelatedField': [*shared_attributes, *shared_relationship_fields_attributes],
    'HyperlinkedIdentityField': [*shared_attributes, *shared_relationship_fields_attributes],
}
