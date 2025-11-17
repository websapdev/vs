'use client'

import { motion } from 'framer-motion'
import FeatureCard from './FeatureCard'

export default function Features() {
  const features = [
    {
      id: 1,
      title: 'QuickScan Audit',
      description: 'Instantly audit your website\'s AI visibility and get comprehensive insights into your search presence across major AI platforms.',
      icon: '📊',
    },
    {
      id: 2,
      title: 'Citation Tracker',
      description: 'Monitor and track all citations of your brand across ChatGPT, Claude, and other AI models in real-time.',
      icon: '🔍',
    },
    {
      id: 3,
      title: 'Answer Graph',
      description: 'Build and visualize your answer graph to understand how your brand appears in AI-generated responses and recommendations.',
      icon: '🌐',
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
      },
    },
  }

  return (
    <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4">
            Powerful Features
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Everything you need to understand and optimize your AI visibility
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
        >
          {features.map((feature) => (
            <FeatureCard key={feature.id} feature={feature} />
          ))}
        </motion.div>
      </div>
    </section>
  )
}
