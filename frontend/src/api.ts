export async function request<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .slice(0, 4)
              .map(
                (e: { loc: (string | number)[]; msg: string }) =>
                  `${e.loc.filter((x) => x !== "body").join(" → ")}: ${e.msg}`,
              )
              .join("; ")
          : "The app could not complete this request. Check that it is running and try again.";
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export const jsonWrite = (value: unknown, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(value),
});
