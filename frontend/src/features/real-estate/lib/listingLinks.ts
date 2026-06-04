export type ListingHouseType = 'one-room' | 'villa' | 'apartment' | 'officetel';

export interface ListingLinkInput {
  dongName: string;
  lat: number;
  lng: number;
  zoom: number;
  houseType: ListingHouseType;
}

export interface ListingLinkItem {
  key: 'naver' | 'zigbang' | 'dabang';
  title: string;
  href: string;
}

const NAVER_COORD_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

const HOUSE_TYPE_MAP: Record<ListingHouseType, {
  naver: string;
  zigbang: string;
  dabang: string;
}> = {
  'one-room': {
    naver: 'C01',
    zigbang: 'oneroom',
    dabang: 'onetwo',
  },
  villa: {
    naver: 'A05-A06-A07-C02-C03',
    zigbang: 'villa',
    dabang: 'house',
  },
  apartment: {
    naver: 'A01',
    zigbang: 'apt',
    dabang: 'apt',
  },
  officetel: {
    naver: 'A02',
    zigbang: 'officetel',
    dabang: 'officetel',
  },
};

export function encodeNaverFinCoord(value: number) {
  let next = BigInt(Math.round((value + 200) * 10_000_000));
  if (next === 0n) return '0';

  let encoded = '';
  while (next > 0n) {
    encoded = NAVER_COORD_ALPHABET[Number(next % 62n)] + encoded;
    next /= 62n;
  }

  return encoded;
}

export function buildNaverFinCenter(lat: number, lng: number) {
  return `${encodeNaverFinCoord(lng)}-${encodeNaverFinCoord(lat)}`;
}

export function buildRealEstateListingLinks({
  dongName,
  lat,
  lng,
  zoom,
  houseType,
}: ListingLinkInput): ListingLinkItem[] {
  const type = HOUSE_TYPE_MAP[houseType];
  const encodedDong = encodeURIComponent(dongName.trim());
  const roundedDabangZoom = Math.round(zoom);
  const naverCenter = buildNaverFinCenter(lat, lng);

  return [
    {
      key: 'naver',
      title: '네이버페이 부동산',
      href: `https://fin.land.naver.com/map?center=${encodeURIComponent(naverCenter)}&zoom=${encodeURIComponent(String(zoom))}&tradeTypes=B1-B2&realEstateTypes=${type.naver}`,
    },
    {
      key: 'zigbang',
      title: '직방',
      href: `https://www.zigbang.com/home/${type.zigbang}/map?search_keyword=${encodedDong}`,
    },
    {
      key: 'dabang',
      title: '다방',
      href: `https://www.dabangapp.com/map/${type.dabang}?m_lat=${lat}&m_lng=${lng}&m_zoom=${roundedDabangZoom}`,
    },
  ];
}
