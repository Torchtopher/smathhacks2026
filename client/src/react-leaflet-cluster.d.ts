declare module "react-leaflet-cluster" {
  import { FC } from "react"
  import type { MarkerClusterGroupOptions } from "leaflet"

  interface MarkerClusterGroupProps extends MarkerClusterGroupOptions {
    children?: React.ReactNode
    chunkedLoading?: boolean
    iconCreateFunction?: (cluster: { getChildCount: () => number }) => L.DivIcon
  }

  const MarkerClusterGroup: FC<MarkerClusterGroupProps>
  export default MarkerClusterGroup
}
