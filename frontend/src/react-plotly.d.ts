declare module 'react-plotly.js' {
  import { Component, CSSProperties } from 'react'

  interface PlotParams {
    data: any[]
    layout?: any
    config?: any
    frames?: any[]
    style?: CSSProperties
    className?: string
    id?: string
    debug?: boolean
    useResizeHandler?: boolean
    onUpdate?: (figure: any, graphDiv: HTMLElement) => void
    onInitialized?: (figure: any, graphDiv: HTMLElement) => void
    onPurge?: (figure: any, graphDiv: HTMLElement) => void
    onError?: (err: Error) => void
    divId?: string
  }

  export default class Plot extends Component<PlotParams> {}
}
