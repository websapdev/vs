'use client'

import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, Zap } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export default function PricingPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()

  const plans = [
    {
      id: 'quickscan',
      name: 'QuickScan',
      price: '$0',
      period: 'forever',
      description: 'Perfect for trying out the platform',
      features: [
        'Up to 3 pages scanned',
        'Base rule pack',
        'Overall score',
        'Basic findings',
        'JSON export',
      ],
      cta: 'Start Free',
      popular: false,
    },
    {
      id: 'full',
      name: 'Full Audit',
      price: '$10',
      period: 'per audit',
      description: 'Comprehensive analysis for serious optimization',
      features: [
        'Up to 12 pages scanned',
        'All rule packs',
        'Detailed scores by category',
        'AI-generated fixes',
        'Acceptance tests',
        'DOCX & Markdown export',
        'Audit history',
      ],
      cta: 'Get Started',
      popular: true,
    },
    {
      id: 'agency',
      name: 'Agency',
      price: '$25',
      period: 'per audit',
      description: 'For agencies managing multiple clients',
      features: [
        'Up to 12 pages scanned',
        'All rule packs',
        'Priority processing',
        'White-label reports',
        'API access',
        'Dedicated support',
        'Team collaboration',
        'Unlimited exports',
      ],
      cta: 'Contact Sales',
      popular: false,
    },
  ]

  const handlePlanSelect = (planId: string) => {
    if (isAuthenticated) {
      if (planId === 'quickscan') {
        router.push('/audit')
      } else {
        router.push('/audit')
      }
    } else {
      router.push('/signup')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="pt-24 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16 space-y-4"
          >
            <h1 className="text-5xl sm:text-6xl font-bold text-gray-900">
              Simple, Transparent Pricing
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Choose the plan that fits your needs. Start free, upgrade anytime.
            </p>
          </motion.div>

          {/* Pricing Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
            {plans.map((plan, index) => (
              <motion.div
                key={plan.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className={`h-full relative ${plan.popular ? 'border-2 border-blue-600 shadow-xl' : ''}`}>
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <Badge className="bg-blue-600 text-white px-4 py-1">
                        <Zap className="w-3 h-3 mr-1" />
                        Most Popular
                      </Badge>
                    </div>
                  )}
                  <CardHeader className="text-center pb-8 pt-8">
                    <CardTitle className="text-2xl mb-2">{plan.name}</CardTitle>
                    <div className="space-y-2">
                      <div>
                        <span className="text-5xl font-bold text-gray-900">{plan.price}</span>
                        <span className="text-gray-600 ml-2">/ {plan.period}</span>
                      </div>
                      <CardDescription className="text-base">{plan.description}</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <ul className="space-y-3">
                      {plan.features.map((feature, idx) => (
                        <li key={idx} className="flex items-start space-x-3">
                          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                          <span className="text-sm text-gray-600">{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button
                      className="w-full"
                      variant={plan.popular ? 'default' : 'outline'}
                      onClick={() => handlePlanSelect(plan.id)}
                    >
                      {plan.cta}
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* FAQ */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="max-w-3xl mx-auto"
          >
            <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">Frequently Asked Questions</h2>
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">What's included in the QuickScan?</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    QuickScan analyzes up to 3 pages of your website and provides basic visibility insights including overall score and key findings. It's perfect for getting started.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Can I upgrade my plan later?</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    Absolutely! You can start with QuickScan and upgrade to Full Audit or Agency plan anytime you need more comprehensive analysis.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">What payment methods do you accept?</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    We accept all major credit cards through Stripe. Enterprise customers can also pay via invoice.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Do you offer refunds?</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    Yes! If you're not satisfied with an audit, contact us within 7 days for a full refund, no questions asked.
                  </p>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        </div>
      </div>

      <Footer />
    </div>
  )
}
