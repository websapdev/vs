'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { toast } from 'sonner'
import { useMutation, useQuery } from '@tanstack/react-query'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import { CheckCircle, Loader2, Target, TrendingUp, XCircle } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

const citationSchema = z.object({
  brand: z.string().min(2, 'Brand name is required'),
  intent: z.string().min(3, 'Search intent is required'),
})

type CitationForm = z.infer<typeof citationSchema>

export default function CitationsPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const [citationResults, setCitationResults] = useState<any>(null)
  const [selectedBrand, setSelectedBrand] = useState<string>('')

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CitationForm>({
    resolver: zodResolver(citationSchema),
  })

  const citationMutation = useMutation({
    mutationFn: async (data: CitationForm) => {
      const response = await apiClient.trackCitations(data.brand, data.intent)
      if (!response.success) {
        throw new Error(response.error || 'Citation tracking failed')
      }
      return response.data
    },
    onSuccess: (data) => {
      setCitationResults(data)
      toast.success('Citation tracking completed!')
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const { data: citationStats } = useQuery({
    queryKey: ['citation-stats', selectedBrand],
    queryFn: async () => {
      if (!selectedBrand) return null
      const response = await apiClient.getCitationStats(selectedBrand)
      return response.data
    },
    enabled: !!selectedBrand && isAuthenticated,
  })

  const onSubmit = (data: CitationForm) => {
    citationMutation.mutate(data)
    setSelectedBrand(data.brand)
  }

  if (!isAuthenticated) {
    return null
  }

  const chartData = citationResults ? [
    { name: 'Cited', value: citationResults.summary.cited, color: '#10b981' },
    { name: 'Not Cited', value: citationResults.summary.total - citationResults.summary.cited, color: '#ef4444' },
  ] : []

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-24 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header */}
          <div className="space-y-2">
            <h1 className="text-4xl font-bold text-gray-900">Citation Tracker</h1>
            <p className="text-lg text-gray-600">Monitor your brand mentions across AI platforms</p>
          </div>

          {/* Tracking Form */}
          <Card>
            <CardHeader>
              <CardTitle>Track Citations</CardTitle>
              <CardDescription>Enter your brand and search intent to check AI citations</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="brand">Brand Name</Label>
                    <Input
                      id="brand"
                      placeholder="e.g., Asana"
                      {...register('brand')}
                      disabled={citationMutation.isPending}
                    />
                    {errors.brand && (
                      <p className="text-sm text-red-600">{errors.brand.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="intent">Search Intent</Label>
                    <Input
                      id="intent"
                      placeholder="e.g., best project management tools"
                      {...register('intent')}
                      disabled={citationMutation.isPending}
                    />
                    {errors.intent && (
                      <p className="text-sm text-red-600">{errors.intent.message}</p>
                    )}
                  </div>
                </div>

                <Button type="submit" className="w-full" disabled={citationMutation.isPending}>
                  {citationMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Tracking citations...
                    </>
                  ) : (
                    <>
                      <Target className="w-4 h-4 mr-2" />
                      Track Citations
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Citation Results */}
          {citationResults && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Summary Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Citation Summary</CardTitle>
                  <CardDescription>Overall citation rate</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-center mb-6">
                    <div className="relative">
                      <svg className="transform -rotate-90 w-32 h-32">
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="#e5e7eb"
                          strokeWidth="10"
                          fill="none"
                        />
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke={citationResults.summary.rate >= 50 ? '#10b981' : '#ef4444'}
                          strokeWidth="10"
                          fill="none"
                          strokeDasharray={`${(citationResults.summary.rate / 100) * 351.8} 351.8`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-bold text-gray-900">
                          {citationResults.summary.rate}%
                        </span>
                        <span className="text-xs text-gray-600">Citation Rate</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Total Checks:</span>
                      <span className="font-medium text-gray-900">{citationResults.summary.total}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Cited:</span>
                      <span className="font-medium text-green-600">{citationResults.summary.cited}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Not Cited:</span>
                      <span className="font-medium text-red-600">{citationResults.summary.total - citationResults.summary.cited}</span>
                    </div>
                  </div>

                  {chartData.length > 0 && (
                    <div className="mt-6">
                      <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                          <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            {chartData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Results by Assistant */}
              <Card>
                <CardHeader>
                  <CardTitle>Results by Assistant</CardTitle>
                  <CardDescription>Citation status per AI platform</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {citationResults.results.map((result: any, index: number) => (
                      <div
                        key={index}
                        className={`p-4 border rounded-lg ${result.cited ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-semibold text-gray-900">{result.assistant}</h4>
                          {result.cited ? (
                            <Badge variant="success">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Cited
                            </Badge>
                          ) : (
                            <Badge variant="error">
                              <XCircle className="w-3 h-3 mr-1" />
                              Not Cited
                            </Badge>
                          )}
                        </div>
                        {result.response && (
                          <div className="mt-3 p-3 bg-white rounded border border-gray-200">
                            <p className="text-sm text-gray-600 line-clamp-3">{result.response}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Historical Stats */}
          {citationStats && (
            <Card>
              <CardHeader>
                <CardTitle>Historical Statistics</CardTitle>
                <CardDescription>Citation performance for {selectedBrand}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <div className="text-3xl font-bold text-blue-600">{citationStats.total_queries}</div>
                    <div className="text-sm text-gray-600 mt-1">Total Queries</div>
                  </div>
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <div className="text-3xl font-bold text-green-600">{citationStats.overall_rate}%</div>
                    <div className="text-sm text-gray-600 mt-1">Overall Rate</div>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <div className="text-3xl font-bold text-purple-600">
                      {citationStats.chatgpt_rate || citationStats.claude_rate || 0}%
                    </div>
                    <div className="text-sm text-gray-600 mt-1">Top Platform</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
