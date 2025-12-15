'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { toast } from 'sonner'
import { useMutation } from '@tanstack/react-query'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/store/authStore'
import { apiClient, Finding } from '@/lib/api'
import { AlertCircle, CheckCircle, FileText, Loader2, XCircle, Download, TrendingUp, AlertTriangle } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const auditSchema = z.object({
  url: z.string().url('Please enter a valid URL'),
  plan: z.enum(['quickscan', 'full', 'agency']),
})

type AuditForm = z.infer<typeof auditSchema>

export default function AuditPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const [auditResult, setAuditResult] = useState<any>(null)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AuditForm>({
    resolver: zodResolver(auditSchema),
    defaultValues: {
      plan: 'quickscan',
    },
  })

  const auditMutation = useMutation({
    mutationFn: async (data: AuditForm) => {
      const response = await apiClient.runAudit(data.url, ['base'], data.plan)
      if (!response.success) {
        throw new Error(response.error || 'Audit failed')
      }
      return response.data
    },
    onSuccess: (data) => {
      setAuditResult(data)
      toast.success('Audit completed successfully!')
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const onSubmit = (data: AuditForm) => {
    auditMutation.mutate(data)
  }

  if (!isAuthenticated) {
    return null
  }

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      seo: '#3b82f6',
      content: '#8b5cf6',
      technical: '#10b981',
      performance: '#f59e0b',
      security: '#ef4444',
    }
    return colors[category.toLowerCase()] || '#6b7280'
  }

  const categoryScores = auditResult?.scores?.by_category
    ? Object.entries(auditResult.scores.by_category).map(([category, score]) => ({
        category,
        score: Math.round(score as number),
      }))
    : []

  const groupedFindings = auditResult?.findings?.reduce((acc: any, finding: Finding) => {
    if (!acc[finding.category]) {
      acc[finding.category] = []
    }
    acc[finding.category].push(finding)
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-24 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header */}
          <div className="space-y-2">
            <h1 className="text-4xl font-bold text-gray-900">Audit Tool</h1>
            <p className="text-lg text-gray-600">Run a comprehensive AI visibility audit on any website</p>
          </div>

          {/* Audit Form */}
          <Card>
            <CardHeader>
              <CardTitle>Run New Audit</CardTitle>
              <CardDescription>Enter a website URL to analyze its AI visibility</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="url">Website URL</Label>
                  <Input
                    id="url"
                    type="url"
                    placeholder="https://example.com"
                    {...register('url')}
                    disabled={auditMutation.isPending}
                  />
                  {errors.url && (
                    <p className="text-sm text-red-600">{errors.url.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label>Select Plan</Label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      { id: 'quickscan', name: 'QuickScan', pages: '3 pages', price: 'Free' },
                      { id: 'full', name: 'Full Audit', pages: '12 pages', price: '$10' },
                      { id: 'agency', name: 'Agency', pages: '12 pages', price: '$25' },
                    ].map((plan) => (
                      <label key={plan.id} className="relative cursor-pointer">
                        <input
                          type="radio"
                          value={plan.id}
                          {...register('plan')}
                          className="peer sr-only"
                          disabled={auditMutation.isPending}
                        />
                        <div className="p-4 border-2 border-gray-200 rounded-lg peer-checked:border-blue-600 peer-checked:bg-blue-50 hover:border-blue-300 transition-all">
                          <div className="font-semibold text-gray-900">{plan.name}</div>
                          <div className="text-sm text-gray-600 mt-1">{plan.pages}</div>
                          <div className="text-sm font-medium text-blue-600 mt-2">{plan.price}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <Button type="submit" className="w-full" disabled={auditMutation.isPending}>
                  {auditMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Running audit...
                    </>
                  ) : (
                    <>
                      <TrendingUp className="w-4 h-4 mr-2" />
                      Run Audit
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Audit Results */}
          {auditResult && (
            <div className="space-y-6">
              {/* Overall Score */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Audit Results</CardTitle>
                      <CardDescription>{auditResult.domain} - {auditResult.page_count} pages scanned</CardDescription>
                    </div>
                    <Badge variant={auditResult.scores.overall >= 80 ? 'success' : auditResult.scores.overall >= 60 ? 'warning' : 'error'}>
                      {auditResult.scores.overall >= 80 ? 'Excellent' : auditResult.scores.overall >= 60 ? 'Good' : 'Needs Improvement'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-center mb-8">
                    <div className="relative">
                      <svg className="transform -rotate-90 w-48 h-48">
                        <circle
                          cx="96"
                          cy="96"
                          r="88"
                          stroke="#e5e7eb"
                          strokeWidth="12"
                          fill="none"
                        />
                        <circle
                          cx="96"
                          cy="96"
                          r="88"
                          stroke={auditResult.scores.overall >= 80 ? '#10b981' : auditResult.scores.overall >= 60 ? '#f59e0b' : '#ef4444'}
                          strokeWidth="12"
                          fill="none"
                          strokeDasharray={`${(auditResult.scores.overall / 100) * 553.2} 553.2`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-5xl font-bold text-gray-900">
                          {Math.round(auditResult.scores.overall)}
                        </span>
                        <span className="text-sm text-gray-600 mt-1">Overall Score</span>
                      </div>
                    </div>
                  </div>

                  {/* Category Scores Chart */}
                  {categoryScores.length > 0 && (
                    <div className="mt-8">
                      <h4 className="text-lg font-semibold text-gray-900 mb-4">Scores by Category</h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={categoryScores}>
                          <XAxis dataKey="category" stroke="#9ca3af" />
                          <YAxis stroke="#9ca3af" />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#ffffff',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px'
                            }}
                          />
                          <Bar dataKey="score" radius={[8, 8, 0, 0]}>
                            {categoryScores.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={getCategoryColor(entry.category)} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Findings by Category */}
              {groupedFindings && Object.keys(groupedFindings).map((category) => (
                <Card key={category}>
                  <CardHeader>
                    <CardTitle className="capitalize">{category} Findings</CardTitle>
                    <CardDescription>{groupedFindings[category].length} checks performed</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {groupedFindings[category].map((finding: Finding, index: number) => (
                        <div
                          key={index}
                          className={`p-4 border rounded-lg ${
                            finding.status === 'pass'
                              ? 'border-green-200 bg-green-50'
                              : finding.status === 'warning'
                              ? 'border-yellow-200 bg-yellow-50'
                              : 'border-red-200 bg-red-50'
                          }`}
                        >
                          <div className="flex items-start space-x-3">
                            {finding.status === 'pass' ? (
                              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                            ) : finding.status === 'warning' ? (
                              <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                            ) : (
                              <XCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                            )}
                            <div className="flex-1">
                              <h5 className="font-semibold text-gray-900">{finding.title}</h5>
                              {finding.why && (
                                <p className="text-sm text-gray-600 mt-1">{finding.why}</p>
                              )}
                              {finding.fix && finding.status !== 'pass' && (
                                <div className="mt-3 p-3 bg-white rounded border border-gray-200">
                                  <p className="text-sm font-medium text-gray-900 mb-1">How to fix:</p>
                                  <p className="text-sm text-gray-600">{finding.fix}</p>
                                  {finding.fix_snippet && (
                                    <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                                      <code>{finding.fix_snippet}</code>
                                    </pre>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
