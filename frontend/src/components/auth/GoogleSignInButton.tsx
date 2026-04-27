import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { authService } from "@src/services/authService";
import { Loader2 } from "lucide-react";

type GoogleButtonMode = "signin" | "signup";

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleButtonOptions = {
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  text?: "signin_with" | "signup_with" | "continue_with";
  shape?: "rectangular" | "pill" | "circle" | "square";
  width?: number;
  logo_alignment?: "left" | "center";
};

type GoogleIdConfiguration = {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void;
  auto_select?: boolean;
};

type GoogleAccountsIdApi = {
  initialize: (config: GoogleIdConfiguration) => void;
  renderButton: (parent: HTMLElement, options: GoogleButtonOptions) => void;
};

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: GoogleAccountsIdApi;
      };
    };
  }
}

const GOOGLE_GSI_SCRIPT_ID = "google-identity-services";

let googleScriptPromise: Promise<void> | null = null;

function loadGoogleScript() {
  if (window.google?.accounts?.id) {
    return Promise.resolve();
  }

  if (!googleScriptPromise) {
    googleScriptPromise = new Promise<void>((resolve, reject) => {
      const existingScript = document.getElementById(
        GOOGLE_GSI_SCRIPT_ID,
      ) as HTMLScriptElement | null;

      if (existingScript) {
        if (existingScript.dataset.loaded === "true") {
          resolve();
          return;
        }

        existingScript.addEventListener("load", () => resolve(), { once: true });
        existingScript.addEventListener(
          "error",
          () => reject(new Error("Không tải được Google Identity Services.")),
          { once: true },
        );
        return;
      }

      const script = document.createElement("script");
      script.id = GOOGLE_GSI_SCRIPT_ID;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = () => {
        script.dataset.loaded = "true";
        resolve();
      };
      script.onerror = () =>
        reject(new Error("Không tải được Google Identity Services."));
      document.head.appendChild(script);
    }).catch((error) => {
      googleScriptPromise = null;
      throw error;
    });
  }

  return googleScriptPromise;
}

function getGoogleButtonText(mode: GoogleButtonMode) {
  return mode === "signup" ? "signup_with" : "continue_with";
}

function getFallbackLabel(mode: GoogleButtonMode) {
  return mode === "signup" ? "Đăng ký với Google" : "Đăng nhập với Google";
}

type GoogleSignInButtonProps = {
  mode: GoogleButtonMode;
  disabled?: boolean;
  onSuccess: (nextPath: string) => void;
  onError?: (message: string | null) => void;
};

export function GoogleSignInButton({
  mode,
  disabled = false,
  onSuccess,
  onError,
}: GoogleSignInButtonProps) {
  const buttonContainerRef = useRef<HTMLDivElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isExchanging, setIsExchanging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const reportError = useCallback(
    (message: string | null) => {
      setLocalError(message);
      onError?.(message);
    },
    [onError],
  );

  const handleGoogleCredential = useCallback(
    async (response: GoogleCredentialResponse) => {
      const credential = response.credential?.trim();

      if (!credential) {
        reportError("Không nhận được Google credential hợp lệ.");
        return;
      }

      setIsExchanging(true);
      reportError(null);

      try {
        const result = await authService.loginWithGoogle({
          credential,
          device: "web",
        });
        onSuccess(result.nextPath);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Không thể đăng nhập với Google lúc này.";
        reportError(message);
      } finally {
        setIsExchanging(false);
      }
    },
    [onSuccess, reportError],
  );

  useEffect(() => {
    let cancelled = false;

    const setupGoogleButton = async () => {
      setIsInitializing(true);
      reportError(null);

      try {
        const config = await authService.getGoogleConfig();

        if (!config.enabled || !config.clientId) {
          reportError("Google sign-in chưa được cấu hình cho môi trường này.");
          return;
        }

        await loadGoogleScript();

        const googleAccounts = window.google?.accounts?.id;
        const buttonContainer = buttonContainerRef.current;

        if (cancelled || !googleAccounts || !buttonContainer) {
          return;
        }

        googleAccounts.initialize({
          client_id: config.clientId,
          callback: (response) => {
            void handleGoogleCredential(response);
          },
          auto_select: false,
        });

        buttonContainer.innerHTML = "";
        googleAccounts.renderButton(buttonContainer, {
          theme: "outline",
          size: "large",
          text: getGoogleButtonText(mode),
          shape: "rectangular",
          logo_alignment: "left",
          width: Math.max(wrapperRef.current?.offsetWidth ?? 320, 280),
        });
      } catch (error) {
        if (!cancelled) {
          const message =
            error instanceof Error
              ? error.message
              : "Không thể tải đăng nhập Google lúc này.";
          reportError(message);
        }
      } finally {
        if (!cancelled) {
          setIsInitializing(false);
        }
      }
    };

    void setupGoogleButton();

    return () => {
      cancelled = true;
    };
  }, [handleGoogleCredential, mode, reportError]);

  return (
    <div className="space-y-2">
      {(isInitializing || localError) && (
        <Button
          variant="outline"
          className="h-11 w-full"
          type="button"
          disabled
        >
          {isInitializing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Đang tải Google...
            </>
          ) : (
            getFallbackLabel(mode)
          )}
        </Button>
      )}

      <div
        ref={wrapperRef}
        className={`w-full ${disabled ? "pointer-events-none opacity-60" : ""} ${
          isInitializing || localError ? "hidden" : ""
        }`}
      >
        <div ref={buttonContainerRef} className="flex justify-center" />
      </div>

      {isExchanging && (
        <p className="text-sm text-muted-foreground">
          Đang xác minh tài khoản Google...
        </p>
      )}

      {localError && <p className="text-sm text-destructive">{localError}</p>}
    </div>
  );
}
