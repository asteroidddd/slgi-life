import L from 'leaflet';
import { CircleMarker, Marker } from 'react-leaflet';

import type { AmenityBboxItem, MedicalFacilityItem } from '@/types/api';

type MapPointItem = AmenityBboxItem | MedicalFacilityItem;

function mapPointKey(item: MapPointItem): string {
  if ('hpid' in item) return `medical-${item.hpid}`;
  return `${item.source_table}-${item.source_id}`;
}

function AmenityLayer({ items, getIcon, onSelect }: { items: MapPointItem[]; getIcon: (category: string) => string; onSelect: (item: MapPointItem) => void }) {
  return (
    <>
      {items.map((item) => {
        if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return null;
        const iconText = getIcon(item.category);
        const icon = L.divIcon({
          className: 'amenity-pin-icon',
          html: `<span style="display:flex;width:30px;height:30px;align-items:center;justify-content:center;border:1px solid rgba(20,83,45,.32);border-radius:999px;background:rgba(255,255,255,.94);box-shadow:0 2px 10px rgba(15,23,42,.22);font-size:16px;font-weight:800;line-height:1;color:#14532d;">${iconText}</span>`,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        });
        const itemKey = mapPointKey(item);
        const handleSelect = (event: L.LeafletMouseEvent) => {
          event.originalEvent.stopPropagation();
          onSelect(item);
        };
        return [
            <Marker
              key={`${itemKey}-icon`}
              position={[item.lat, item.lng]}
              icon={icon}
              eventHandlers={{ click: handleSelect }}
            />,
            <CircleMarker
              key={`${itemKey}-hit`}
              center={[item.lat, item.lng]}
              radius={16}
              pathOptions={{
                color: 'transparent',
                weight: 0,
                fillColor: '#22c55e',
                fillOpacity: 0.01,
              }}
              eventHandlers={{
                click: handleSelect,
              }}
            />
        ];
      })}
    </>
  );
}

export default AmenityLayer;
