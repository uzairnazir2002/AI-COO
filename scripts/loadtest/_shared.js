export function requiredEnv(name) {
  const value = __ENV[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

export function readOrgIds() {
  const orgIdsJson = requiredEnv("ORG_IDS_JSON");
  let parsed = [];
  try {
    parsed = JSON.parse(orgIdsJson);
  } catch (error) {
    throw new Error(`ORG_IDS_JSON must be a JSON array: ${error}`);
  }
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("ORG_IDS_JSON must be a non-empty JSON array");
  }
  return parsed;
}

export function selectOrg(orgIds) {
  return orgIds[__VU % orgIds.length];
}

export function isoMondayOrToday() {
  return __ENV.WEEK_START || new Date().toISOString().slice(0, 10);
}

export function commonHeaders(accessToken) {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}
