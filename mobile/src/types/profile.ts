export type Profile = {
  username: string;
  full_name: string;
  profile_picture: string | null;
  cover_photo: string | null;
  bio: string;
  website: string;
  location: string;
  date_joined: string;
  account_type: "personal" | "creator" | "business";
  is_verified: boolean;
  is_private: boolean;
  followers_count: number;
  following_count: number;
  posts_count: number;
  reels_count: number;
  is_following: boolean;
  viewer_can_view_private_content: boolean;
  mutual_followers_count: number;
  tabs: string[];
  phone_number?: string;
  email?: string;
  date_of_birth?: string;
};

export type PrivacySettings = {
  show_in_suggestions: boolean;
  phone_discoverable: boolean;
  dob_visibility: "hidden" | "month_day" | "full";
  profile_details_public: boolean;
  online_status_visible: boolean;
};

export type Paginated<T> = {
  results: T[];
  count: number;
  next_offset: number | null;
};

export type CompactUser = {
  username: string;
  full_name: string;
  profile_picture: string | null;
  is_private: boolean;
  is_verified: boolean;
  is_following: boolean;
  mutual_followers_count: number;
};
