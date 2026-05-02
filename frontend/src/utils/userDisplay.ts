export type AvatarLikeUser = {
  name?: string | null;
  email?: string | null;
  avatarUrl?: string | null;
  avatar_url?: string | null;
  picture?: string | null;
  photoURL?: string | null;
  image?: string | null;
  googlePicture?: string | null;
};

export function getUserAvatarUrl(user?: AvatarLikeUser | null) {
  if (!user) return "";

  return (
    user.avatarUrl ||
    user.avatar_url ||
    user.picture ||
    user.photoURL ||
    user.image ||
    user.googlePicture ||
    ""
  ).trim();
}

export function buildUserInitials(name?: string | null, email?: string | null) {
  const source = (name || email || "GG").trim();
  if (!source) return "GG";

  const words = source
    .replace(/@.*$/, "")
    .split(/\s+/)
    .filter(Boolean);

  if (words.length <= 1) {
    return words[0].slice(0, 2).toUpperCase();
  }

  return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}
