// Scenario hero photos per city (files and credits: public/cities/CREDITS.md). Unknown city -> undefined (keep the gradient).
export type CityPhoto = { src: string; credit: string };

const PHOTOS: Record<string, CityPhoto> = {
  Houston: { src: '/cities/houston.jpg', credit: 'Photo: David Daniel Turner, CC BY 4.0, via Wikimedia Commons' },
  Dallas: { src: '/cities/dallas.jpg', credit: 'Photo: BullDawg2021, CC BY 4.0, via Wikimedia Commons' },
};

export function cityPhoto(city: string | undefined): CityPhoto | undefined {
  return city ? PHOTOS[city] : undefined;
}
