from back.core.views import Routes
from back.views.auth import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    OAuthCallbackView,
    OAuthStartView,
    RegisterView,
    ResetPasswordView,
)
from back.views.catalog import (
    CategoriesView,
    FlavorWheelView,
    OffersView,
    OfferView,
    RecommendationsView,
    ShopCheckView,
    ShopLogoView,
    ShopsView,
    ShopView,
    TeaBrewingView,
    TeaFlavorsView,
    TeaImageView,
    TeaPricesView,
    TeasView,
    TeaView,
    UserFlavorsView,
)
from back.views.diary import DiaryEntryView, DiaryView
from back.views.feedback import FeedbackView
from back.views.frontend import (
    AssetView,
    MediaView,
    NotFoundView,
    OgImageView,
    PublicFileView,
    RobotsView,
    SitemapView,
    SpaView,
    YandexVerificationView,
)
from back.views.health import HealthView
from back.views.rankings import CategoryLeadersView, CategoryRankingView, ShopRankingView, TopTeasView
from back.views.reviews import (
    RecentReviewsView,
    ReviewPhotosView,
    ReviewPhotoView,
    ReviewView,
    ReviewVoteView,
    TeaReviewsView,
    UserReviewsView,
)
from back.views.social import AuthorView, FeedView, FollowingView, FollowView, ShelfItemView, ShelfView


class ApiRoutes(Routes):
    prefix = "/api"
    tags = ("api",)
    views = (HealthView, FeedbackView)


class AuthRoutes(Routes):
    prefix = "/api/auth"
    tags = ("auth",)
    views = (
        RegisterView,
        LoginView,
        LogoutView,
        MeView,
        OAuthStartView,
        OAuthCallbackView,
        ForgotPasswordView,
        ResetPasswordView,
    )


class CatalogRoutes(Routes):
    prefix = "/api"
    tags = ("catalog",)
    views = (
        CategoriesView,
        FlavorWheelView,
        ShopsView,
        ShopCheckView,  # раньше ShopView: иначе «check» примут за имя магазина
        ShopView,
        ShopLogoView,
        TeasView,
        TeaView,
        TeaImageView,
        TeaFlavorsView,
        TeaBrewingView,
        TeaPricesView,
        UserFlavorsView,
        RecommendationsView,
        OffersView,
        OfferView,
    )


class RankingRoutes(Routes):
    prefix = "/api/rankings"
    tags = ("rankings",)
    views = (CategoryRankingView, CategoryLeadersView, ShopRankingView, TopTeasView)


class ReviewRoutes(Routes):
    prefix = "/api"
    tags = ("reviews",)
    views = (
        RecentReviewsView,
        UserReviewsView,
        TeaReviewsView,
        ReviewView,
        ReviewVoteView,
        ReviewPhotosView,
        ReviewPhotoView,
    )


class SocialRoutes(Routes):
    prefix = "/api"
    tags = ("social",)
    views = (AuthorView, FollowView, FollowingView, FeedView, ShelfView, ShelfItemView)


class DiaryRoutes(Routes):
    prefix = "/api/diary"
    tags = ("diary",)
    views = (DiaryView, DiaryEntryView)


class FrontendRoutes(Routes):
    # NotFoundView ловит всё подряд — он обязан быть последним
    views = (
        AssetView,
        MediaView,
        OgImageView,
        PublicFileView,
        RobotsView,
        SitemapView,
        YandexVerificationView,
        SpaView,
        NotFoundView,
    )


#: Порядок подключения: сначала API, потом фронт с его catch-all.
ROUTES: tuple[type[Routes], ...] = (
    ApiRoutes,
    AuthRoutes,
    CatalogRoutes,
    RankingRoutes,
    ReviewRoutes,
    DiaryRoutes,
    SocialRoutes,
    FrontendRoutes,
)
