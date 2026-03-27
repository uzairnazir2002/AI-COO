export type PlaidLinkSuccessMetadata = {
  institution?: {
    name?: string | null;
    institution_id?: string | null;
  } | null;
  accounts?: Array<{
    id?: string;
    name?: string;
    mask?: string | null;
    subtype?: string | null;
    type?: string | null;
  }>;
  [key: string]: unknown;
};

export type PlaidLinkExitError = {
  error_type?: string;
  error_code?: string;
  error_message?: string;
  display_message?: string;
  [key: string]: unknown;
};

export type PlaidLinkHandler = {
  open: () => void;
  exit: (options?: { force?: boolean }, callback?: () => void) => void;
  destroy: () => void;
};

export type PlaidCreateConfig = {
  token: string;
  onSuccess: (publicToken: string, metadata: PlaidLinkSuccessMetadata) => void;
  onExit?: (error: PlaidLinkExitError | null, metadata: PlaidLinkSuccessMetadata) => void;
  onEvent?: (eventName: string, metadata: PlaidLinkSuccessMetadata) => void;
};

export type PlaidFactory = {
  create: (config: PlaidCreateConfig) => PlaidLinkHandler;
};

declare global {
  interface Window {
    Plaid?: PlaidFactory;
  }
}
