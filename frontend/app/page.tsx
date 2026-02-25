import { getStockData } from '@/lib/data'
import { Dashboard } from '@/components/Dashboard'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export default async function Home() {
  const data = await getStockData()

  return <Dashboard initialData={data} />
}
