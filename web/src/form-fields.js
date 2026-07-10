const CONTROL_CHARACTER_PATTERN = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/u;
const PHONE_PATTERN = /^\+?[0-9][0-9 .()/-]{5,31}$/u;
const GENERIC_POSTAL_PATTERN = /^[\p{L}\p{N}][\p{L}\p{N} .'-]{1,15}$/u;
const HOST_LABEL_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/u;
const MAC_PATTERN = /^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/u;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/u;
const TEXT_MAX_LENGTH = 512;
const TEXTAREA_MAX_LENGTH = 262144;

const COUNTRY_POSTAL_PATTERNS = Object.freeze({
  BE: /^\d{4}$/u,
  CA: /^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$/u,
  CH: /^\d{4}$/u,
  DE: /^\d{5}$/u,
  ES: /^\d{5}$/u,
  FR: /^\d{5}$/u,
  GB: /^(?:GIR 0AA|[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2})$/iu,
  IT: /^\d{5}$/u,
  NL: /^\d{4} ?[A-Za-z]{2}$/u,
  PT: /^\d{4}-\d{3}$/u,
  US: /^\d{5}(?:-\d{4})?$/u,
});

const DATETIME_NAME_PATTERN = /(?:^|_)(?:observed_at|observed_before|received_at|created_at|updated_at|expires_at|expired_at|valid_from|valid_to|window_start|window_end|first_seen|last_seen|started_at|ended_at|occurred_at|timestamp)(?:$|_)/u;
const DATE_NAME_PATTERN = /(?:^|_)(?:date|start_date|end_date|warranty_start|warranty_end|support_start|support_end|entitlement_start|entitlement_end)(?:$|_)/u;

function normalizedDescriptor(field) {
  return `${field?.name || ''} ${field?.label || ''} ${field?.placeholder || ''}`
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/gu, '')
    .toLowerCase();
}

function slugifyFieldName(label, index = 0) {
  const slug = String(label || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/gu, '_')
    .replace(/^_+|_+$/gu, '');
  return slug || `field_${index}`;
}

export function normalizeFieldDefinition(field, index = 0) {
  if (typeof field === 'string') {
    const normalized = { name: slugifyFieldName(field, index), label: field };
    return { ...normalized, validation: inferValidationKind(normalized) };
  }
  const normalized = { ...field };
  normalized.name ||= slugifyFieldName(normalized.label, index);
  normalized.label ||= normalized.name;
  normalized.validation ||= inferValidationKind(normalized);
  return normalized;
}

export function inferValidationKind(field) {
  const explicitType = String(field?.type || '').toLowerCase();
  if (['select', 'boolean', 'hidden', 'tenant-select', 'organization-select', 'partner-select', 'country-select'].includes(explicitType)) return 'selection';
  if (explicitType === 'number') return 'number';
  if (explicitType === 'json') return 'json';
  if (explicitType === 'csv') return 'csv';
  if (explicitType === 'date') return 'date';
  if (explicitType === 'datetime-local' || field?.format === 'date-time') return 'datetime';
  if (field?.format === 'date') return 'date';

  const descriptor = normalizedDescriptor(field);
  const name = String(field?.name || '').toLowerCase();
  if (DATETIME_NAME_PATTERN.test(name) || /iso[- ]?8601|date et heure|date\/heure|datetime|timestamp|premier evenement|dernier evenement|debut fenetre|fin fenetre|observe le|observed at|\d{2}:\d{2}/u.test(descriptor)) return 'datetime';
  if (DATE_NAME_PATTERN.test(name) || /\bdate\b/u.test(descriptor)) return 'date';
  if (/(?:^|_)(?:email|mail)(?:$|_)/u.test(name) || /\bemail\b|courriel/u.test(descriptor)) return 'email';
  if (/(?:^|_)(?:phone|telephone|tel)(?:$|_)/u.test(name) || /telephone|phone/u.test(descriptor)) return 'phone';
  if (/(?:^|_)(?:postal_code|postcode|zip_code|zip)(?:$|_)/u.test(name) || /code postal|postal code|\bcp\b/u.test(descriptor)) return 'postal-code';
  if (/(?:^|_)(?:mac|mac_address)(?:$|_)/u.test(name) || /adresse mac|mac address/u.test(descriptor)) return 'mac';
  if (/(?:^|_)(?:cidr|prefix)(?:$|_)/u.test(name) || /\bcidr\b|prefixe|prefix|aggregate|reseau ip|ip network/u.test(descriptor)) return 'cidr';
  if (/(?:^|_)(?:management_ip|source_ip|destination_ip|peer_address|ip_address|address_ip|ip)(?:$|_)/u.test(name) || /adresse ip|ip source|ip destination|management ip/u.test(descriptor)) return 'ip';
  if (/(?:^|_)(?:website|url|endpoint_url|instance_url|backend_url)(?:$|_)/u.test(name) || /site web|\burl\b|endpoint https/u.test(descriptor)) return 'url';
  if (/(?:^|_)(?:hostname|fqdn|dns_name)(?:$|_)/u.test(name) || /nom dns|hostname|fqdn/u.test(descriptor)) return 'hostname';
  if (/\bjson\b/u.test(descriptor)) return 'json';
  return 'text';
}

export function inputTypeForField(field) {
  const normalized = normalizeFieldDefinition(field);
  switch (normalized.validation) {
    case 'date': return 'date';
    case 'datetime': return 'datetime-local';
    case 'email': return 'email';
    case 'phone': return 'tel';
    case 'url': return 'url';
    case 'number': return 'number';
    default: return 'text';
  }
}

export function inputAttributesForField(field) {
  const normalized = normalizeFieldDefinition(field);
  const textLike = !['date', 'datetime', 'number', 'selection'].includes(normalized.validation);
  const attributes = {};
  if (textLike) attributes.maxLength = normalized.maxLength || (normalized.type === 'textarea' || normalized.type === 'json' ? TEXTAREA_MAX_LENGTH : TEXT_MAX_LENGTH);
  if (normalized.validation === 'email') {
    attributes.autoComplete = 'email';
    attributes.inputMode = 'email';
    attributes.maxLength = Math.min(attributes.maxLength || 254, 254);
  } else if (normalized.validation === 'phone') {
    attributes.autoComplete = 'tel';
    attributes.inputMode = 'tel';
    attributes.maxLength = Math.min(attributes.maxLength || 32, 32);
    attributes.pattern = '\\+?[0-9][0-9 .()/-]{5,31}';
  } else if (normalized.validation === 'postal-code') {
    attributes.autoComplete = 'postal-code';
    attributes.maxLength = Math.min(attributes.maxLength || 16, 16);
  } else if (normalized.validation === 'ip' || normalized.validation === 'cidr') {
    attributes.autoComplete = 'off';
    attributes.inputMode = 'text';
    attributes.maxLength = Math.min(attributes.maxLength || 64, 64);
  } else if (normalized.validation === 'mac') {
    attributes.autoComplete = 'off';
    attributes.maxLength = Math.min(attributes.maxLength || 17, 17);
    attributes.pattern = '(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}';
  } else if (normalized.validation === 'hostname') {
    attributes.autoComplete = 'off';
    attributes.maxLength = Math.min(attributes.maxLength || 253, 253);
  } else if (normalized.validation === 'url') {
    attributes.autoComplete = 'url';
    attributes.inputMode = 'url';
    attributes.maxLength = Math.min(attributes.maxLength || 2048, 2048);
  } else if (normalized.validation === 'date' || normalized.validation === 'datetime') {
    attributes.autoComplete = 'off';
  } else if (normalized.validation === 'number') {
    attributes.inputMode = 'decimal';
    if (normalized.min !== undefined) attributes.min = normalized.min;
    if (normalized.max !== undefined) attributes.max = normalized.max;
    if (normalized.step !== undefined) attributes.step = normalized.step;
  }
  return attributes;
}

function isValidIpv4(value) {
  const parts = value.split('.');
  return parts.length === 4 && parts.every((part) => /^\d{1,3}$/u.test(part) && Number(part) <= 255 && part === String(Number(part)));
}

function isValidIpv6(value) {
  if (!value.includes(':') || /\s/u.test(value)) return false;
  try {
    const parsed = new URL(`http://[${value}]/`);
    return parsed.hostname.startsWith('[') && parsed.hostname.endsWith(']');
  } catch {
    return false;
  }
}

export function isValidIpAddress(value) {
  return isValidIpv4(value) || isValidIpv6(value);
}

export function isValidCidr(value) {
  const parts = value.split('/');
  if (parts.length !== 2 || !/^\d{1,3}$/u.test(parts[1])) return false;
  const address = parts[0];
  const prefix = Number(parts[1]);
  return isValidIpv4(address) ? prefix >= 0 && prefix <= 32 : isValidIpv6(address) && prefix >= 0 && prefix <= 128;
}

function isValidHostname(value) {
  const normalized = value.endsWith('.') ? value.slice(0, -1) : value;
  return normalized.length > 0 && normalized.length <= 253 && normalized.split('.').every((label) => HOST_LABEL_PATTERN.test(label));
}

function isValidDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
}

function isValidDateTime(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?(?:Z|[+-]\d{2}:\d{2})?$/u.test(value)) return false;
  return !Number.isNaN(new Date(value).getTime());
}

function isValidUrl(value) {
  try {
    const parsed = new URL(value);
    return ['http:', 'https:'].includes(parsed.protocol) && Boolean(parsed.hostname);
  } catch {
    return false;
  }
}

function postalCodePattern(countryCode) {
  return COUNTRY_POSTAL_PATTERNS[String(countryCode || '').trim().toUpperCase()] || GENERIC_POSTAL_PATTERN;
}

export function validateFieldValue(field, rawValue, context = {}) {
  const normalized = normalizeFieldDefinition(field);
  const value = rawValue === undefined || rawValue === null ? '' : String(rawValue).trim();
  if (!value) return normalized.required ? { valid: false, code: 'requiredField', value } : { valid: true, value: undefined };
  if (CONTROL_CHARACTER_PATTERN.test(value)) return { valid: false, code: 'invalidText', value };
  if (value.length > (normalized.maxLength || (normalized.type === 'textarea' || normalized.type === 'json' ? TEXTAREA_MAX_LENGTH : TEXT_MAX_LENGTH))) return { valid: false, code: 'invalidText', value };

  let valid = true;
  switch (normalized.validation) {
    case 'number': valid = Number.isFinite(Number(value)); break;
    case 'email': valid = value.length <= 254 && EMAIL_PATTERN.test(value); break;
    case 'phone': valid = PHONE_PATTERN.test(value); break;
    case 'postal-code': valid = postalCodePattern(context.countryCode).test(value); break;
    case 'ip': valid = isValidIpAddress(value); break;
    case 'cidr': valid = isValidCidr(value); break;
    case 'mac': valid = MAC_PATTERN.test(value); break;
    case 'hostname': valid = isValidHostname(value); break;
    case 'url': valid = isValidUrl(value); break;
    case 'date': valid = isValidDate(value); break;
    case 'datetime': valid = isValidDateTime(value); break;
    case 'json':
      try { JSON.parse(value); } catch { valid = false; }
      break;
    case 'csv': valid = value.split(',').every((part) => part.trim() && !CONTROL_CHARACTER_PATTERN.test(part)); break;
    default: valid = true;
  }
  return { valid, code: valid ? null : `invalid${normalized.validation.split('-').map((part) => part[0].toUpperCase() + part.slice(1)).join('')}`, value };
}

export function normalizeFieldValue(field, rawValue, context = {}) {
  const normalized = normalizeFieldDefinition(field);
  const validation = validateFieldValue(normalized, rawValue, context);
  if (!validation.valid) {
    const error = new Error(validation.code || 'invalidField');
    error.code = validation.code || 'invalidField';
    error.field = normalized;
    throw error;
  }
  if (validation.value === undefined) return undefined;
  const value = validation.value;
  switch (normalized.validation) {
    case 'number': return Number(value);
    case 'json': return JSON.parse(value);
    case 'csv': return value.split(',').map((item) => item.trim()).filter(Boolean);
    case 'postal-code': return value.toUpperCase();
    case 'datetime': return new Date(value).toISOString();
    default: return value;
  }
}

export function fieldValidationMessage(i18n, result, field) {
  const normalized = normalizeFieldDefinition(field);
  const key = result?.code || 'invalidField';
  return i18n?.t?.(key, { field: i18n.label(normalized.label || normalized.name) }) || `${normalized.label || normalized.name}: ${key}`;
}

export function validateControl(control, field, i18n, context = {}) {
  const result = validateFieldValue(field, control.value, context);
  const message = result.valid ? '' : fieldValidationMessage(i18n, result, field);
  control.setCustomValidity(message);
  control.setAttribute('aria-invalid', result.valid ? 'false' : 'true');
  return result.valid;
}

export function formCountryCode(form) {
  const control = form?.querySelector?.('[name="country"], [name="country_code"], [data-field="country"], [data-field="country_code"]');
  return control?.value || '';
}
