import { redirect } from "next/navigation";

export default async function ReplayRedirectPage({ params }: { params: Promise<{ cityId: string }> }) {
  const { cityId } = await params;
  redirect(`/cities/${cityId}/simulate`);
}
