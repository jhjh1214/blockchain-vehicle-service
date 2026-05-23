export interface MYCity {
  city: string;
  state: string;
  lat: number;
  lng: number;
}

export const MY_CITIES: MYCity[] = [
  { city: 'Kuala Lumpur',      state: 'W.P. Kuala Lumpur',  lat: 3.1390,  lng: 101.6869 },
  { city: 'Petaling Jaya',     state: 'Selangor',            lat: 3.1073,  lng: 101.6067 },
  { city: 'Shah Alam',         state: 'Selangor',            lat: 3.0733,  lng: 101.5185 },
  { city: 'Subang Jaya',       state: 'Selangor',            lat: 3.0499,  lng: 101.5830 },
  { city: 'Cyberjaya',         state: 'Selangor',            lat: 2.9213,  lng: 101.6559 },
  { city: 'Klang',             state: 'Selangor',            lat: 3.0449,  lng: 101.4455 },
  { city: 'Rawang',            state: 'Selangor',            lat: 3.3194,  lng: 101.5738 },
  { city: 'Kajang',            state: 'Selangor',            lat: 2.9925,  lng: 101.7870 },
  { city: 'Putrajaya',         state: 'W.P. Putrajaya',      lat: 2.9264,  lng: 101.6964 },
  { city: 'Seremban',          state: 'Negeri Sembilan',     lat: 2.7297,  lng: 101.9381 },
  { city: 'Port Dickson',      state: 'Negeri Sembilan',     lat: 2.5228,  lng: 101.7988 },
  { city: 'Johor Bahru',       state: 'Johor',               lat: 1.4927,  lng: 103.7414 },
  { city: 'Batu Pahat',        state: 'Johor',               lat: 1.8530,  lng: 102.9345 },
  { city: 'Muar',              state: 'Johor',               lat: 2.0442,  lng: 102.5689 },
  { city: 'Kluang',            state: 'Johor',               lat: 2.0284,  lng: 103.3172 },
  { city: 'Georgetown',        state: 'Penang',               lat: 5.4141,  lng: 100.3288 },
  { city: 'Butterworth',       state: 'Penang',               lat: 5.3992,  lng: 100.3636 },
  { city: 'Ipoh',              state: 'Perak',                lat: 4.5975,  lng: 101.0901 },
  { city: 'Taiping',           state: 'Perak',                lat: 4.8500,  lng: 100.7333 },
  { city: 'Teluk Intan',       state: 'Perak',                lat: 4.0227,  lng: 101.0228 },
  { city: 'Melaka',            state: 'Melaka',               lat: 2.1896,  lng: 102.2501 },
  { city: 'Alor Setar',        state: 'Kedah',                lat: 6.1248,  lng: 100.3678 },
  { city: 'Sungai Petani',     state: 'Kedah',                lat: 5.6478,  lng: 100.4933 },
  { city: 'Kangar',            state: 'Perlis',               lat: 6.4449,  lng: 100.1986 },
  { city: 'Kuantan',           state: 'Pahang',               lat: 3.8077,  lng: 103.3260 },
  { city: 'Temerloh',          state: 'Pahang',               lat: 3.4504,  lng: 102.4195 },
  { city: 'Kota Bharu',        state: 'Kelantan',             lat: 6.1254,  lng: 102.2381 },
  { city: 'Kuala Terengganu',  state: 'Terengganu',           lat: 5.3302,  lng: 103.1408 },
  { city: 'Kuching',           state: 'Sarawak',              lat: 1.5533,  lng: 110.3592 },
  { city: 'Miri',              state: 'Sarawak',              lat: 4.3995,  lng: 113.9914 },
  { city: 'Sibu',              state: 'Sarawak',              lat: 2.2890,  lng: 111.8261 },
  { city: 'Kota Kinabalu',     state: 'Sabah',                lat: 5.9804,  lng: 116.0735 },
  { city: 'Sandakan',          state: 'Sabah',                lat: 5.8402,  lng: 118.1179 },
  { city: 'Tawau',             state: 'Sabah',                lat: 4.2453,  lng: 117.8908 },
];

export function getCityCoords(cityName: string): { lat: number; lng: number } | null {
  const found = MY_CITIES.find(c => c.city.toLowerCase() === cityName?.toLowerCase());
  return found ? { lat: found.lat, lng: found.lng } : null;
}

export function getStateForCity(cityName: string): string {
  return MY_CITIES.find(c => c.city.toLowerCase() === cityName?.toLowerCase())?.state ?? '';
}
