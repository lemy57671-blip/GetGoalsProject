import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-lg rounded-[28px] border-border">
        <CardContent className="space-y-4 p-8 text-center">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-primary">
            404
          </p>
          <h1 className="text-3xl font-bold text-foreground">
            Route chua duoc migrate
          </h1>
          <p className="text-muted-foreground">
            Shell React da san sang, nhung route nay chua duoc port UI tu Next.js.
          </p>
          <Button asChild>
            <Link to="/">Quay ve landing shell</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
