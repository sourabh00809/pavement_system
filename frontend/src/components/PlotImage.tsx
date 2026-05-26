export default function PlotImage({ src, alt = 'Plot' }: { src: string; alt?: string }) {
  if (!src) return null
  return (
    <div className="card overflow-hidden">
      <img src={`data:image/png;base64,${src}`} alt={alt} className="w-full h-auto" />
    </div>
  )
}
