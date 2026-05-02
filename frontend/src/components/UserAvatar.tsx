"use client";

import { useEffect, useState } from "react";

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar";
import {
  buildUserInitials,
  getUserAvatarUrl,
  type AvatarLikeUser,
} from "@src/utils/userDisplay";

type UserAvatarProps = AvatarLikeUser & {
  avatarUrl?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClasses = {
  sm: "h-8 w-8 text-sm",
  md: "h-10 w-10 text-base",
  lg: "h-20 w-20 text-2xl",
};

export function UserAvatar({
  name,
  email,
  avatarUrl,
  avatar_url,
  picture,
  photoURL,
  image,
  googlePicture,
  size = "md",
  className = "",
}: UserAvatarProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const resolvedAvatarUrl = getUserAvatarUrl({
    name,
    email,
    avatarUrl,
    avatar_url,
    picture,
    photoURL,
    image,
    googlePicture,
  });
  const initials = buildUserInitials(name, email);

  useEffect(() => {
    setImageFailed(false);
  }, [resolvedAvatarUrl]);

  return (
    <Avatar className={`${sizeClasses[size]} ${className}`}>
      {resolvedAvatarUrl && !imageFailed ? (
        <AvatarImage
          src={resolvedAvatarUrl}
          alt={name || email || "User avatar"}
          onError={() => setImageFailed(true)}
        />
      ) : null}
      <AvatarFallback className="bg-primary/10 font-semibold text-primary">
        {initials}
      </AvatarFallback>
    </Avatar>
  );
}
