import Foundation
import Observation
import Security

struct UserProfile: Codable, Sendable {
    let userId: UUID
    let displayName: String?
    let countryCode: String?
    let regionCode: String?
    let locationSource: String?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case displayName = "display_name"
        case countryCode = "country_code"
        case regionCode = "region_code"
        case locationSource = "location_source"
    }
}

struct OnboardingProfile: Codable, Sendable {
    let status: String
    let nextStep: String
    let userId: UUID
    let countryCode: String?
    let regionCode: String?
    let locationSource: String?
    let privacyNoticeVersion: String?
    let privacyNoticeAcknowledgedAt: Date?
    let dietPattern: String?
    let allergyStatus: String
    let allergens: [String]
    let dietaryRules: [String]
    let cuisinePreferenceStatus: String
    let cuisineAreas: [String]
    let proteins: [String]
    let completedAt: Date?
    let updatedAt: Date?

    var isCompleted: Bool {
        status == "completed"
    }

    enum CodingKeys: String, CodingKey {
        case status
        case nextStep = "next_step"
        case userId = "user_id"
        case countryCode = "country_code"
        case regionCode = "region_code"
        case locationSource = "location_source"
        case privacyNoticeVersion = "privacy_notice_version"
        case privacyNoticeAcknowledgedAt = "privacy_notice_acknowledged_at"
        case dietPattern = "diet_pattern"
        case allergyStatus = "allergy_status"
        case allergens
        case dietaryRules = "dietary_rules"
        case cuisinePreferenceStatus = "cuisine_preference_status"
        case cuisineAreas = "cuisine_areas"
        case proteins
        case completedAt = "completed_at"
        case updatedAt = "updated_at"
    }
}

struct CountryReference: Codable, Identifiable, Sendable {
    let code: String
    let name: String
    let seasonalDataAvailable: Bool
    let availabilityMessage: String?

    var id: String { code }

    var displayName: String {
        guard let availabilityMessage, !seasonalDataAvailable else { return name }
        return "\(name) (\(availabilityMessage))"
    }

    enum CodingKeys: String, CodingKey {
        case code
        case name
        case seasonalDataAvailable = "seasonal_data_available"
        case availabilityMessage = "availability_message"
    }
}

struct CuisineReference: Codable, Identifiable, Sendable {
    let area: String

    var id: String { area }
}

struct EnumReference: Codable, Identifiable, Sendable {
    let value: String
    let label: String

    var id: String { value }
}

struct SeasonalRecipeList: Codable, Sendable {
    let countryCode: String
    let month: Int
    let page: Int
    let pageSize: Int
    let total: Int
    let items: [SeasonalRecipe]

    enum CodingKeys: String, CodingKey {
        case countryCode = "country_code"
        case month
        case page
        case pageSize = "page_size"
        case total
        case items
    }
}

struct RecommendationFeed: Codable, Sendable {
    let slateId: UUID
    let countryCode: String
    let month: Int
    let rankingStrategy: String
    let personalized: Bool
    let total: Int
    let items: [SeasonalRecipe]

    enum CodingKeys: String, CodingKey {
        case slateId = "slate_id"
        case countryCode = "country_code"
        case month
        case rankingStrategy = "ranking_strategy"
        case personalized
        case total
        case items
    }
}

struct SeasonalRecipe: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let name: String
    let category: String?
    let area: String?
    let countryOfOrigin: String?
    let thumbnailURL: URL?
    let instructions: String?
    let matchedSeasonalProduce: [String]
    let matchedSeasonalProduceCount: Int

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case category
        case area
        case countryOfOrigin = "country_of_origin"
        case thumbnailURL = "thumbnail_url"
        case instructions
        case matchedSeasonalProduce = "matched_seasonal_produce"
        case matchedSeasonalProduceCount = "matched_seasonal_produce_count"
    }
}

struct RecipeSummary: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let name: String
    let category: String?
    let area: String?
    let countryOfOrigin: String?
    let thumbnailURL: URL?

    var seasonalRecipe: SeasonalRecipe {
        SeasonalRecipe(
            id: id,
            name: name,
            category: category,
            area: area,
            countryOfOrigin: countryOfOrigin,
            thumbnailURL: thumbnailURL,
            instructions: nil,
            matchedSeasonalProduce: [],
            matchedSeasonalProduceCount: 0
        )
    }

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case category
        case area
        case countryOfOrigin = "country_of_origin"
        case thumbnailURL = "thumbnail_url"
    }
}

struct FavouriteRecipe: Codable, Sendable {
    let recipe: RecipeSummary
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case recipe
        case createdAt = "created_at"
    }
}

struct RecipeHistoryItem: Codable, Sendable {
    let recipe: RecipeSummary
    let viewedAt: Date

    enum CodingKeys: String, CodingKey {
        case recipe
        case viewedAt = "viewed_at"
    }
}

struct PlannedMealRequest: Encodable {
    let recipeId: UUID
    let dayOfWeek: Int
    let mealSlot: String

    enum CodingKeys: String, CodingKey {
        case recipeId = "recipe_id"
        case dayOfWeek = "day_of_week"
        case mealSlot = "meal_slot"
    }
}

struct RemotePlannedMeal: Codable, Identifiable, Sendable {
    let id: UUID
    let recipe: RecipeSummary
    let dayOfWeek: Int
    let mealSlot: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case recipe
        case dayOfWeek = "day_of_week"
        case mealSlot = "meal_slot"
        case createdAt = "created_at"
    }
}

struct PersonalizationConsent: Codable, Sendable {
    let active: Bool
    let noticeVersion: String
    let grantedAt: Date?
    let retentionDays: Int

    enum CodingKeys: String, CodingKey {
        case active
        case noticeVersion = "notice_version"
        case grantedAt = "granted_at"
        case retentionDays = "retention_days"
    }
}

struct PersonalizationConsentUpdate: Encodable {
    let explicitConsent: Bool

    enum CodingKeys: String, CodingKey {
        case explicitConsent = "explicit_consent"
    }
}

struct RecommendationImpression: Encodable {
    let eventId: UUID
    let recipeId: UUID
    let position: Int

    enum CodingKeys: String, CodingKey {
        case eventId = "event_id"
        case recipeId = "recipe_id"
        case position
    }
}

struct RecommendationImpressionBatch: Encodable {
    let slateId: UUID
    let impressions: [RecommendationImpression]

    enum CodingKeys: String, CodingKey {
        case slateId = "slate_id"
        case impressions
    }
}

private struct RecommendationImpressionBatchResponse: Decodable {
    let received: Int
}

struct SeasonalProduce: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let name: String
    let type: String
    let mealdbName: String?
    let countryCode: String
    let countryName: String
    let month: Int
    let sourceName: String
    let sourceURL: URL?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case type
        case mealdbName = "mealdb_name"
        case countryCode = "country_code"
        case countryName = "country_name"
        case month
        case sourceName = "source_name"
        case sourceURL = "source_url"
    }
}

struct SeasonalProduceGroups: Codable, Hashable, Sendable {
    let fruits: [SeasonalProduce]
    let vegetables: [SeasonalProduce]

    static let empty = SeasonalProduceGroups(fruits: [], vegetables: [])

    var all: [SeasonalProduce] {
        fruits + vegetables
    }
}

struct SeasonlyUser: Codable, Sendable {
    let id: UUID
    let email: String
    let isActive: Bool
    let isVerified: Bool
    let createdAt: Date
    let updatedAt: Date
    let profile: UserProfile?

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case isActive = "is_active"
        case isVerified = "is_verified"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case profile
    }
}

struct TokenResponse: Codable, Sendable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
    }
}

private struct RegistrationRequest: Encodable {
    let email: String
    let password: String
    let profile: RegistrationProfile?
}

private struct RegistrationProfile: Encodable {
    let displayName: String

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
    }
}

private struct RefreshTokenRequest: Codable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

private struct PasswordResetRequest: Encodable {
    let email: String
}

private struct PasswordResetConfirmRequest: Encodable {
    let resetToken: String
    let newPassword: String

    enum CodingKeys: String, CodingKey {
        case resetToken = "reset_token"
        case newPassword = "new_password"
    }
}

struct CurrentPasswordRequest: Encodable {
    let currentPassword: String

    enum CodingKeys: String, CodingKey {
        case currentPassword = "current_password"
    }
}

struct AccountDeletionRequest: Encodable {
    let currentPassword: String
    let confirmation: String

    enum CodingKeys: String, CodingKey {
        case currentPassword = "current_password"
        case confirmation
    }
}

struct PrivacyAcknowledgeRequest: Encodable {
    let acknowledged: Bool
}

struct LocationUpdateRequest: Encodable {
    let countryCode: String
    let regionCode: String?
    let source: String

    enum CodingKeys: String, CodingKey {
        case countryCode = "country_code"
        case regionCode = "region_code"
        case source
    }
}

struct DietUpdateRequest: Encodable {
    let dietPattern: String

    enum CodingKeys: String, CodingKey {
        case dietPattern = "diet_pattern"
    }
}

struct AllergyUpdateRequest: Encodable {
    let status: String
    let allergens: [String]
    let explicitConsent: Bool

    enum CodingKeys: String, CodingKey {
        case status
        case allergens
        case explicitConsent = "explicit_consent"
    }
}

struct DietaryRulesUpdateRequest: Encodable {
    let dietaryRules: [String]

    enum CodingKeys: String, CodingKey {
        case dietaryRules = "dietary_rules"
    }
}

struct CuisineUpdateRequest: Encodable {
    let status: String
    let areas: [String]
}

struct ProteinUpdateRequest: Encodable {
    let proteins: [String]
}

private struct MessageResponse: Decodable {
    let message: String
}

private struct APIErrorResponse: Decodable {
    let detail: APIErrorDetail
}

private enum APIErrorDetail: Decodable {
    case message(String)
    case validation([ValidationIssue])
    case completion(OnboardingCompletionIssues)

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let message = try? container.decode(String.self) {
            self = .message(message)
        } else if let completion = try? container.decode(OnboardingCompletionIssues.self) {
            self = .completion(completion)
        } else {
            self = .validation(try container.decode([ValidationIssue].self))
        }
    }

    var message: String {
        switch self {
        case .message(let message):
            return message
        case .validation(let issues):
            return issues.first?.message ?? "The request could not be completed."
        case .completion(let completion):
            return completion.errors.joined(separator: "\n")
        }
    }
}

private struct OnboardingCompletionIssues: Decodable {
    let errors: [String]
}

private struct ValidationIssue: Decodable {
    let message: String

    enum CodingKeys: String, CodingKey {
        case message = "msg"
    }
}

enum AuthenticationError: LocalizedError {
    case invalidResponse
    case unauthorized
    case server(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an unexpected response."
        case .unauthorized:
            return "Your session has expired. Please sign in again."
        case .server(let message):
            return message
        }
    }
}

struct AuthenticationClient: Sendable {
    private let baseURL: URL
    private let session: URLSession
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    init(baseURL: URL = AuthenticationClient.defaultBaseURL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
    }

    static var defaultBaseURL: URL {
        let configuredValue = ProcessInfo.processInfo.environment["SEASONLY_API_BASE_URL"]
            ?? Bundle.main.object(forInfoDictionaryKey: "SEASONLY_API_BASE_URL") as? String
        if let configuredValue,
           !configuredValue.isEmpty,
           let url = URL(string: configuredValue) {
#if !DEBUG
            precondition(url.scheme == "https", "Release API endpoints must use HTTPS")
#endif
            return url
        }
#if DEBUG
        return URL(string: "http://127.0.0.1:8001/api/v1")!
#else
        preconditionFailure("SEASONLY_API_BASE_URL is required for release builds")
#endif
    }

    func login(email: String, password: String) async throws -> TokenResponse {
        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "username", value: email),
            URLQueryItem(name: "password", value: password)
        ]

        var request = request(path: "auth/token", method: "POST")
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = components.percentEncodedQuery?.data(using: .utf8)
        return try await send(request)
    }

    func register(email: String, password: String, displayName: String) async throws -> SeasonlyUser {
        let profile = displayName.isEmpty ? nil : RegistrationProfile(displayName: displayName)
        let payload = RegistrationRequest(email: email, password: password, profile: profile)
        return try await sendJSON(path: "users", method: "POST", payload: payload)
    }

    func currentUser(accessToken: String) async throws -> SeasonlyUser {
        var request = request(path: "users/me", method: "GET")
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        return try await send(request)
    }

    func exportUserData(
        accessToken: String,
        currentPassword: String
    ) async throws -> Data {
        var request = request(path: "users/me/data-export", method: "POST")
        authorize(&request, accessToken: accessToken)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(
            CurrentPasswordRequest(currentPassword: currentPassword)
        )
        return try await sendData(request)
    }

    func deleteAccount(
        accessToken: String,
        currentPassword: String,
        confirmation: String
    ) async throws {
        let _: EmptyResponse = try await sendAuthorizedJSON(
            path: "users/me",
            method: "DELETE",
            accessToken: accessToken,
            payload: AccountDeletionRequest(
                currentPassword: currentPassword,
                confirmation: confirmation
            )
        )
    }

    func refresh(refreshToken: String) async throws -> TokenResponse {
        try await sendJSON(
            path: "auth/refresh",
            method: "POST",
            payload: RefreshTokenRequest(refreshToken: refreshToken)
        )
    }

    func logout(refreshToken: String) async throws {
        let _: EmptyResponse = try await sendJSON(
            path: "auth/logout",
            method: "POST",
            payload: RefreshTokenRequest(refreshToken: refreshToken)
        )
    }

    func requestPasswordReset(email: String) async throws -> String {
        let response: MessageResponse = try await sendJSON(
            path: "auth/password-reset/request",
            method: "POST",
            payload: PasswordResetRequest(email: email)
        )
        return response.message
    }

    func confirmPasswordReset(resetToken: String, newPassword: String) async throws -> String {
        let response: MessageResponse = try await sendJSON(
            path: "auth/password-reset/confirm",
            method: "POST",
            payload: PasswordResetConfirmRequest(
                resetToken: resetToken,
                newPassword: newPassword
            )
        )
        return response.message
    }

    func onboardingProfile(accessToken: String) async throws -> OnboardingProfile {
        var request = request(path: "me/onboarding", method: "GET")
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func acknowledgePrivacy(accessToken: String) async throws -> OnboardingProfile {
        try await sendAuthorizedJSON(
            path: "me/onboarding/privacy",
            method: "PUT",
            accessToken: accessToken,
            payload: PrivacyAcknowledgeRequest(acknowledged: true)
        )
    }

    func updateLocation(accessToken: String, payload: LocationUpdateRequest) async throws -> OnboardingProfile {
        try await sendAuthorizedJSON(
            path: "me/onboarding/location",
            method: "PUT",
            accessToken: accessToken,
            payload: payload
        )
    }

    func updateDiet(accessToken: String, payload: DietUpdateRequest) async throws -> OnboardingProfile {
        try await sendAuthorizedJSON(
            path: "me/onboarding/diet",
            method: "PUT",
            accessToken: accessToken,
            payload: payload
        )
    }

    func updateAllergies(accessToken: String, payload: AllergyUpdateRequest) async throws -> OnboardingProfile {
        try await sendAuthorizedJSON(
            path: "me/onboarding/allergies",
            method: "PUT",
            accessToken: accessToken,
            payload: payload
        )
    }

    func updateDietaryRules(
        accessToken: String,
        payload: DietaryRulesUpdateRequest
    ) async throws -> OnboardingProfile {
        try await sendAuthorizedJSON(
            path: "me/onboarding/dietary-rules",
            method: "PUT",
            accessToken: accessToken,
            payload: payload
        )
    }

    func updateCuisines(accessToken: String, payload: CuisineUpdateRequest) async throws -> OnboardingProfile {
        try await sendAuthorizedJSON(
            path: "me/onboarding/cuisines",
            method: "PUT",
            accessToken: accessToken,
            payload: payload
        )
    }

    func updateProteins(accessToken: String, payload: ProteinUpdateRequest) async throws -> OnboardingProfile {
        try await sendAuthorizedJSON(
            path: "me/onboarding/proteins",
            method: "PUT",
            accessToken: accessToken,
            payload: payload
        )
    }

    func completeOnboarding(accessToken: String) async throws -> OnboardingProfile {
        var request = request(path: "me/onboarding/complete", method: "POST")
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func personalizationConsent(accessToken: String) async throws -> PersonalizationConsent {
        var request = request(path: "me/recommendations/consent", method: "GET")
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func grantPersonalizationConsent(
        accessToken: String
    ) async throws -> PersonalizationConsent {
        try await sendAuthorizedJSON(
            path: "me/recommendations/consent",
            method: "PUT",
            accessToken: accessToken,
            payload: PersonalizationConsentUpdate(explicitConsent: true)
        )
    }

    func withdrawPersonalizationConsent(accessToken: String) async throws {
        var request = request(path: "me/recommendations/consent", method: "DELETE")
        authorize(&request, accessToken: accessToken)
        let _: EmptyResponse = try await send(request)
    }

    func recordRecommendationImpressions(
        accessToken: String,
        payload: RecommendationImpressionBatch
    ) async throws {
        let _: RecommendationImpressionBatchResponse = try await sendAuthorizedJSON(
            path: "me/recommendations/impressions",
            method: "POST",
            accessToken: accessToken,
            payload: payload
        )
    }

    func recommendationFeed(
        accessToken: String,
        month: Int? = nil,
        limit: Int = 24
    ) async throws -> RecommendationFeed {
        var queryItems = [
            URLQueryItem(name: "limit", value: "\(limit)")
        ]
        if let month {
            queryItems.append(URLQueryItem(name: "month", value: "\(month)"))
        }

        var request = request(
            path: "me/recommendations/feed",
            method: "GET",
            queryItems: queryItems
        )
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func countries() async throws -> [CountryReference] {
        let request = request(path: "reference/countries", method: "GET")
        return try await send(request)
    }

    func cuisines() async throws -> [CuisineReference] {
        let request = request(path: "reference/cuisines", method: "GET")
        return try await send(request)
    }

    func allergens() async throws -> [EnumReference] {
        let request = request(path: "reference/allergens", method: "GET")
        return try await send(request)
    }

    func proteins() async throws -> [EnumReference] {
        let request = request(path: "reference/proteins", method: "GET")
        return try await send(request)
    }

    func seasonalRecipes(
        accessToken: String,
        month: Int? = nil,
        pageSize: Int = 20,
        area: String? = nil
    ) async throws -> SeasonalRecipeList {
        var queryItems = [
            URLQueryItem(name: "page_size", value: "\(pageSize)")
        ]
        if let month {
            queryItems.append(URLQueryItem(name: "month", value: "\(month)"))
        }
        if let area, !area.isEmpty {
            queryItems.append(URLQueryItem(name: "area", value: area))
        }

        var request = request(path: "recipes/seasonal", method: "GET", queryItems: queryItems)
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func seasonalProduce(countryCode: String, month: Int) async throws -> SeasonalProduceGroups {
        let request = request(
            path: "produce/seasonal",
            method: "GET",
            queryItems: [
                URLQueryItem(name: "country", value: countryCode),
                URLQueryItem(name: "month", value: "\(month)")
            ]
        )
        return try await send(request)
    }

    func favourites(accessToken: String) async throws -> [FavouriteRecipe] {
        var request = request(path: "me/favourites", method: "GET")
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func saveFavourite(accessToken: String, recipeId: UUID) async throws -> FavouriteRecipe {
        var request = request(path: "me/favourites/\(recipeId.uuidString)", method: "PUT")
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func deleteFavourite(accessToken: String, recipeId: UUID) async throws {
        var request = request(path: "me/favourites/\(recipeId.uuidString)", method: "DELETE")
        authorize(&request, accessToken: accessToken)
        let _: EmptyResponse = try await send(request)
    }

    func recipeHistory(accessToken: String, limit: Int = 20) async throws -> [RecipeHistoryItem] {
        var request = request(
            path: "me/history/recipes",
            method: "GET",
            queryItems: [URLQueryItem(name: "limit", value: "\(limit)")]
        )
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func recordRecipeHistory(accessToken: String, recipeId: UUID) async throws -> RecipeHistoryItem {
        var request = request(path: "me/history/recipes/\(recipeId.uuidString)", method: "PUT")
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func clearRecipeHistory(accessToken: String) async throws {
        var request = request(path: "me/history/recipes", method: "DELETE")
        authorize(&request, accessToken: accessToken)
        let _: EmptyResponse = try await send(request)
    }

    func plannedMeals(accessToken: String) async throws -> [RemotePlannedMeal] {
        var request = request(path: "me/planner", method: "GET")
        authorize(&request, accessToken: accessToken)
        return try await send(request)
    }

    func savePlannedMeal(accessToken: String, payload: PlannedMealRequest) async throws -> RemotePlannedMeal {
        try await sendAuthorizedJSON(
            path: "me/planner",
            method: "POST",
            accessToken: accessToken,
            payload: payload
        )
    }

    func deletePlannedMeal(accessToken: String, plannedMealId: UUID) async throws {
        var request = request(path: "me/planner/\(plannedMealId.uuidString)", method: "DELETE")
        authorize(&request, accessToken: accessToken)
        let _: EmptyResponse = try await send(request)
    }

    private func sendJSON<Response: Decodable, Payload: Encodable>(
        path: String,
        method: String,
        payload: Payload
    ) async throws -> Response {
        var request = request(path: path, method: method)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(payload)
        return try await send(request)
    }

    private func sendAuthorizedJSON<Response: Decodable, Payload: Encodable>(
        path: String,
        method: String,
        accessToken: String,
        payload: Payload
    ) async throws -> Response {
        var request = request(path: path, method: method)
        authorize(&request, accessToken: accessToken)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(payload)
        return try await send(request)
    }

    private func request(path: String, method: String) -> URLRequest {
        request(path: path, method: method, queryItems: [])
    }

    private func request(path: String, method: String, queryItems: [URLQueryItem]) -> URLRequest {
        let url = baseURL.appendingPathComponent(path)
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        components?.queryItems = queryItems.isEmpty ? nil : queryItems
        var request = URLRequest(url: components?.url ?? url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        return request
    }

    private func authorize(_ request: inout URLRequest, accessToken: String) {
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
    }

    private func send<Response: Decodable>(_ request: URLRequest) async throws -> Response {
        let data = try await sendData(request)
        if Response.self == EmptyResponse.self, data.isEmpty {
            return EmptyResponse() as! Response
        }
        return try decoder.decode(Response.self, from: data)
    }

    private func sendData(_ request: URLRequest) async throws -> Data {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw AuthenticationError.invalidResponse
        }

        if httpResponse.statusCode == 401 {
            throw AuthenticationError.unauthorized
        }

        guard 200..<300 ~= httpResponse.statusCode else {
            let apiError = try? decoder.decode(APIErrorResponse.self, from: data)
            throw AuthenticationError.server(apiError?.detail.message ?? "Request failed (\(httpResponse.statusCode)).")
        }

        return data
    }
}

private struct EmptyResponse: Decodable {
}

private struct TokenStore {
    private let service = "com.seasonly.authentication"
    private let account = "session-tokens"

    func save(_ tokens: TokenResponse) throws {
        let data = try JSONEncoder().encode(tokens)
        let query = baseQuery
        let updates: [String: Any] = [kSecValueData as String: data]
        var status = SecItemUpdate(query as CFDictionary, updates as CFDictionary)
        if status == errSecItemNotFound {
            var attributes = query
            attributes[kSecValueData as String] = data
            attributes[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            status = SecItemAdd(attributes as CFDictionary, nil)
        }
        guard status == errSecSuccess else {
            throw AuthenticationError.server("The session could not be saved securely.")
        }
    }

    func load() -> TokenResponse? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else {
            return nil
        }
        return try? JSONDecoder().decode(TokenResponse.self, from: data)
    }

    func clear() {
        SecItemDelete(baseQuery as CFDictionary)
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
    }
}

@MainActor
@Observable
final class AuthenticationSession {
    private(set) var user: SeasonlyUser?
    private(set) var onboardingProfile: OnboardingProfile?
    private(set) var personalizationConsent: PersonalizationConsent?
    private(set) var isRestoring = true
    private(set) var isLoading = false
    var errorMessage: String?

    private let client: AuthenticationClient
    private let tokenStore = TokenStore()
    private var tokens: TokenResponse?
    private var refreshTask: Task<TokenResponse, Error>?

    init(client: AuthenticationClient? = nil) {
        self.client = client ?? AuthenticationClient()
    }

    func restore() async {
        defer { isRestoring = false }
        guard let storedTokens = tokenStore.load() else { return }
        tokens = storedTokens

        do {
            user = try await client.currentUser(accessToken: storedTokens.accessToken)
            onboardingProfile = try? await client.onboardingProfile(accessToken: storedTokens.accessToken)
            personalizationConsent = try? await client.personalizationConsent(
                accessToken: storedTokens.accessToken
            )
        } catch AuthenticationError.unauthorized {
            do {
                let refreshedTokens = try await client.refresh(refreshToken: storedTokens.refreshToken)
                try tokenStore.save(refreshedTokens)
                tokens = refreshedTokens
                user = try await client.currentUser(accessToken: refreshedTokens.accessToken)
                onboardingProfile = try? await client.onboardingProfile(accessToken: refreshedTokens.accessToken)
                personalizationConsent = try? await client.personalizationConsent(
                    accessToken: refreshedTokens.accessToken
                )
            } catch {
                personalizationConsent = nil
                tokens = nil
                tokenStore.clear()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func login(email: String, password: String) async -> Bool {
        await performAuthentication {
            try await client.login(email: email, password: password)
        }
    }

    func register(email: String, password: String, displayName: String) async -> Bool {
        await performAuthentication {
            _ = try await client.register(email: email, password: password, displayName: displayName)
            return try await client.login(email: email, password: password)
        }
    }

    func requestPasswordReset(email: String) async -> String? {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            return try await client.requestPasswordReset(email: email)
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func confirmPasswordReset(resetToken: String, newPassword: String) async -> String? {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            return try await client.confirmPasswordReset(
                resetToken: resetToken,
                newPassword: newPassword
            )
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func loadOnboardingProfile() async {
        do {
            onboardingProfile = try await withAuthorizedAccess { accessToken in
                try await client.onboardingProfile(accessToken: accessToken)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadPersonalizationConsent() async -> Bool {
        errorMessage = nil
        do {
            personalizationConsent = try await withAuthorizedAccess { accessToken in
                try await client.personalizationConsent(accessToken: accessToken)
            }
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func updatePersonalizationConsent(enabled: Bool) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            if enabled {
                personalizationConsent = try await withAuthorizedAccess { accessToken in
                    try await client.grantPersonalizationConsent(accessToken: accessToken)
                }
            } else {
                try await withAuthorizedAccess { accessToken in
                    try await client.withdrawPersonalizationConsent(accessToken: accessToken)
                }
                personalizationConsent = try await withAuthorizedAccess { accessToken in
                    try await client.personalizationConsent(accessToken: accessToken)
                }
            }
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func exportUserData(currentPassword: String) async -> Data? {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            return try await withAuthorizedAccess { accessToken in
                try await client.exportUserData(
                    accessToken: accessToken,
                    currentPassword: currentPassword
                )
            }
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func deleteAccount(
        currentPassword: String,
        confirmation: String
    ) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            try await withAuthorizedAccess { accessToken in
                try await client.deleteAccount(
                    accessToken: accessToken,
                    currentPassword: currentPassword,
                    confirmation: confirmation
                )
            }
            clearLocalSession()
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func fetchOnboardingReferences() async -> ([CountryReference], [CuisineReference], [EnumReference], [EnumReference])? {
        do {
            async let countries = client.countries()
            async let cuisines = client.cuisines()
            async let allergens = client.allergens()
            async let proteins = client.proteins()
            return try await (countries, cuisines, allergens, proteins)
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func acknowledgePrivacy() async -> Bool {
        await updateOnboarding { accessToken in
            try await client.acknowledgePrivacy(accessToken: accessToken)
        }
    }

    func updateLocation(countryCode: String, regionCode: String?, source: String) async -> Bool {
        await updateOnboarding { accessToken in
            try await client.updateLocation(
                accessToken: accessToken,
                payload: LocationUpdateRequest(countryCode: countryCode, regionCode: regionCode, source: source)
            )
        }
    }

    func updateDiet(_ dietPattern: String) async -> Bool {
        await updateOnboarding { accessToken in
            try await client.updateDiet(
                accessToken: accessToken,
                payload: DietUpdateRequest(dietPattern: dietPattern)
            )
        }
    }

    func updateAllergies(status: String, allergens: [String], explicitConsent: Bool) async -> Bool {
        await updateOnboarding { accessToken in
            try await client.updateAllergies(
                accessToken: accessToken,
                payload: AllergyUpdateRequest(
                    status: status,
                    allergens: allergens,
                    explicitConsent: explicitConsent
                )
            )
        }
    }

    func updateDietaryRules(_ dietaryRules: [String]) async -> Bool {
        await updateOnboarding { accessToken in
            try await client.updateDietaryRules(
                accessToken: accessToken,
                payload: DietaryRulesUpdateRequest(dietaryRules: dietaryRules)
            )
        }
    }

    func updateCuisines(status: String, areas: [String]) async -> Bool {
        await updateOnboarding { accessToken in
            try await client.updateCuisines(
                accessToken: accessToken,
                payload: CuisineUpdateRequest(status: status, areas: areas)
            )
        }
    }

    func updateProteins(_ proteins: [String]) async -> Bool {
        await updateOnboarding { accessToken in
            try await client.updateProteins(
                accessToken: accessToken,
                payload: ProteinUpdateRequest(proteins: proteins)
            )
        }
    }

    func completeOnboarding() async -> Bool {
        let didComplete = await updateOnboarding { accessToken in
            try await client.completeOnboarding(accessToken: accessToken)
        }
        if didComplete {
            user = try? await withAuthorizedAccess { accessToken in
                try await client.currentUser(accessToken: accessToken)
            }
        }
        return didComplete
    }

    func fetchSeasonalRecipes(pageSize: Int = 20, area: String? = nil) async -> SeasonalRecipeList? {
        do {
            return try await withAuthorizedAccess { accessToken in
                try await client.seasonalRecipes(
                    accessToken: accessToken,
                    pageSize: pageSize,
                    area: area
                )
            }
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func fetchRecommendationFeed(limit: Int = 24) async -> SeasonalRecipeList? {
        do {
            return try await withAuthorizedAccess { accessToken in
                let feed = try await client.recommendationFeed(
                    accessToken: accessToken,
                    limit: limit
                )
                if personalizationConsent?.active == true, !feed.items.isEmpty {
                    let impressions = feed.items.enumerated().map { index, recipe in
                        RecommendationImpression(
                            eventId: UUID(),
                            recipeId: recipe.id,
                            position: index + 1
                        )
                    }
                    try? await client.recordRecommendationImpressions(
                        accessToken: accessToken,
                        payload: RecommendationImpressionBatch(
                            slateId: feed.slateId,
                            impressions: impressions
                        )
                    )
                }
                return SeasonalRecipeList(
                    countryCode: feed.countryCode,
                    month: feed.month,
                    page: 1,
                    pageSize: limit,
                    total: feed.total,
                    items: feed.items
                )
            }
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func fetchSeasonalProduce(countryCode: String, month: Int = Calendar.current.component(.month, from: Date())) async -> SeasonalProduceGroups {
        do {
            return try await client.seasonalProduce(countryCode: countryCode, month: month)
        } catch {
            errorMessage = error.localizedDescription
            return .empty
        }
    }

    func fetchFavourites() async -> [SeasonalRecipe] {
        do {
            return try await withAuthorizedAccess { accessToken in
                try await client.favourites(accessToken: accessToken)
                    .map { $0.recipe.seasonalRecipe }
            }
        } catch {
            errorMessage = error.localizedDescription
            return []
        }
    }

    func saveFavourite(recipeId: UUID) async {
        do {
            _ = try await withAuthorizedAccess { accessToken in
                try await client.saveFavourite(accessToken: accessToken, recipeId: recipeId)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteFavourite(recipeId: UUID) async {
        do {
            try await withAuthorizedAccess { accessToken in
                try await client.deleteFavourite(accessToken: accessToken, recipeId: recipeId)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func fetchRecipeHistory() async -> [SeasonalRecipe] {
        do {
            return try await withAuthorizedAccess { accessToken in
                try await client.recipeHistory(accessToken: accessToken)
                    .map { $0.recipe.seasonalRecipe }
            }
        } catch {
            errorMessage = error.localizedDescription
            return []
        }
    }

    func recordRecipeHistory(recipeId: UUID) async {
        do {
            _ = try await withAuthorizedAccess { accessToken in
                try await client.recordRecipeHistory(
                    accessToken: accessToken,
                    recipeId: recipeId
                )
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func fetchPlannedMeals() async -> [RemotePlannedMeal] {
        do {
            return try await withAuthorizedAccess { accessToken in
                try await client.plannedMeals(accessToken: accessToken)
            }
        } catch {
            errorMessage = error.localizedDescription
            return []
        }
    }

    func savePlannedMeal(recipeId: UUID, dayOfWeek: Int, mealSlot: String) async -> RemotePlannedMeal? {
        do {
            return try await withAuthorizedAccess { accessToken in
                try await client.savePlannedMeal(
                    accessToken: accessToken,
                    payload: PlannedMealRequest(
                        recipeId: recipeId,
                        dayOfWeek: dayOfWeek,
                        mealSlot: mealSlot
                    )
                )
            }
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func deletePlannedMeal(id: UUID) async {
        do {
            try await withAuthorizedAccess { accessToken in
                try await client.deletePlannedMeal(
                    accessToken: accessToken,
                    plannedMealId: id
                )
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func logout() async {
        let refreshToken = tokens?.refreshToken
        clearLocalSession()

        if let refreshToken {
            try? await client.logout(refreshToken: refreshToken)
        }
    }

    private func clearLocalSession() {
        refreshTask?.cancel()
        refreshTask = nil
        user = nil
        onboardingProfile = nil
        personalizationConsent = nil
        tokens = nil
        tokenStore.clear()
    }

    private func performAuthentication(
        getTokens: () async throws -> TokenResponse
    ) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let newTokens = try await getTokens()
            let authenticatedUser = try await client.currentUser(accessToken: newTokens.accessToken)
            try tokenStore.save(newTokens)
            tokens = newTokens
            user = authenticatedUser
            onboardingProfile = try await client.onboardingProfile(accessToken: newTokens.accessToken)
            personalizationConsent = try? await client.personalizationConsent(
                accessToken: newTokens.accessToken
            )
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    private func updateOnboarding(
        operation: (String) async throws -> OnboardingProfile
    ) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            onboardingProfile = try await withAuthorizedAccess(operation: operation)
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    private func withAuthorizedAccess<Response>(
        operation: (String) async throws -> Response
    ) async throws -> Response {
        guard let accessToken = tokens?.accessToken else {
            throw AuthenticationError.unauthorized
        }

        do {
            return try await operation(accessToken)
        } catch AuthenticationError.unauthorized {
            let refreshedTokens = try await refreshSession()
            return try await operation(refreshedTokens.accessToken)
        }
    }

    private func refreshSession() async throws -> TokenResponse {
        if let refreshTask {
            return try await refreshTask.value
        }
        guard let refreshToken = tokens?.refreshToken else {
            throw AuthenticationError.unauthorized
        }

        let task = Task { try await client.refresh(refreshToken: refreshToken) }
        refreshTask = task
        defer { refreshTask = nil }

        do {
            let refreshedTokens = try await task.value
            try tokenStore.save(refreshedTokens)
            tokens = refreshedTokens
            return refreshedTokens
        } catch {
            user = nil
            onboardingProfile = nil
            personalizationConsent = nil
            tokens = nil
            tokenStore.clear()
            throw error
        }
    }
}
