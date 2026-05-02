export const PUBLIC_PATHS = [
  "/",
  "/login",
  "/register",
  "/pricing",
  "/forgot-password",
  "/reset-password",
  "/payment-success",
  "/payment-cancel",
];

export function isProtectedPath(pathname: string) {
  return !PUBLIC_PATHS.some(
    (publicPath) =>
      pathname === publicPath || pathname.startsWith(`${publicPath}/`),
  );
}
