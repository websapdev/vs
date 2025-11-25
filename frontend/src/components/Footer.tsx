export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="bg-gray-100 border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center text-gray-600">
          <p className="text-lg font-medium">
            © {currentYear} Vysalytica. All rights reserved.
          </p>
          <p className="text-sm mt-2">
            Visibility Intelligence for AI-Powered Brands
          </p>
        </div>
      </div>
    </footer>
  )
}
