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

    var id: String { code }
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
    case server(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an unexpected response."
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
        if let override = ProcessInfo.processInfo.environment["SEASONLY_API_BASE_URL"],
           let url = URL(string: override) {
            return url
        }
        return URL(string: "http://127.0.0.1:8001/api/v1")!
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

    func seasonalProduce(countryCode: String, month: Int) async throws -> [SeasonalProduce] {
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
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw AuthenticationError.invalidResponse
        }

        guard 200..<300 ~= httpResponse.statusCode else {
            let apiError = try? decoder.decode(APIErrorResponse.self, from: data)
            throw AuthenticationError.server(apiError?.detail.message ?? "Request failed (\(httpResponse.statusCode)).")
        }

        if Response.self == EmptyResponse.self, data.isEmpty {
            return EmptyResponse() as! Response
        }
        return try decoder.decode(Response.self, from: data)
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
        SecItemDelete(query as CFDictionary)

        var attributes = query
        attributes[kSecValueData as String] = data
        let status = SecItemAdd(attributes as CFDictionary, nil)
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
    private(set) var isRestoring = true
    private(set) var isLoading = false
    var errorMessage: String?

    private let client: AuthenticationClient
    private let tokenStore = TokenStore()
    private var tokens: TokenResponse?

    init(client: AuthenticationClient? = nil) {
        self.client = client ?? AuthenticationClient()
    }

    func restore() async {
        defer { isRestoring = false }
        guard let storedTokens = tokenStore.load() else { return }

        do {
            user = try await client.currentUser(accessToken: storedTokens.accessToken)
            onboardingProfile = try? await client.onboardingProfile(accessToken: storedTokens.accessToken)
            tokens = storedTokens
        } catch {
            do {
                let refreshedTokens = try await client.refresh(refreshToken: storedTokens.refreshToken)
                try tokenStore.save(refreshedTokens)
                tokens = refreshedTokens
                user = try await client.currentUser(accessToken: refreshedTokens.accessToken)
                onboardingProfile = try? await client.onboardingProfile(accessToken: refreshedTokens.accessToken)
            } catch {
                tokenStore.clear()
            }
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

    func loadOnboardingProfile() async {
        guard let accessToken = tokens?.accessToken else { return }

        do {
            onboardingProfile = try await client.onboardingProfile(accessToken: accessToken)
        } catch {
            errorMessage = error.localizedDescription
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
        if didComplete, let accessToken = tokens?.accessToken {
            user = try? await client.currentUser(accessToken: accessToken)
        }
        return didComplete
    }

    func fetchSeasonalRecipes(pageSize: Int = 20, area: String? = nil) async -> SeasonalRecipeList? {
        guard let accessToken = tokens?.accessToken else {
            errorMessage = "Your session has expired. Please sign in again."
            return nil
        }

        do {
            let list = try await client.seasonalRecipes(accessToken: accessToken, pageSize: pageSize, area: area)
            print("Seasonly recipes debug: loaded \(list.items.count) of \(list.total) recipes for \(list.countryCode), month \(list.month)")
            return list
        } catch {
            print("Seasonly recipes debug: failed to load seasonal recipes: \(error.localizedDescription)")
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func fetchSeasonalProduce(countryCode: String, month: Int = Calendar.current.component(.month, from: Date())) async -> [SeasonalProduce] {
        do {
            return try await client.seasonalProduce(countryCode: countryCode, month: month)
        } catch {
            errorMessage = error.localizedDescription
            return []
        }
    }

    func fetchFavourites() async -> [SeasonalRecipe] {
        guard let accessToken = tokens?.accessToken else { return [] }

        do {
            return try await client.favourites(accessToken: accessToken).map { $0.recipe.seasonalRecipe }
        } catch {
            errorMessage = error.localizedDescription
            return []
        }
    }

    func saveFavourite(recipeId: UUID) async {
        guard let accessToken = tokens?.accessToken else { return }

        do {
            _ = try await client.saveFavourite(accessToken: accessToken, recipeId: recipeId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteFavourite(recipeId: UUID) async {
        guard let accessToken = tokens?.accessToken else { return }

        do {
            try await client.deleteFavourite(accessToken: accessToken, recipeId: recipeId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func fetchRecipeHistory() async -> [SeasonalRecipe] {
        guard let accessToken = tokens?.accessToken else { return [] }

        do {
            return try await client.recipeHistory(accessToken: accessToken).map { $0.recipe.seasonalRecipe }
        } catch {
            errorMessage = error.localizedDescription
            return []
        }
    }

    func recordRecipeHistory(recipeId: UUID) async {
        guard let accessToken = tokens?.accessToken else { return }

        do {
            _ = try await client.recordRecipeHistory(accessToken: accessToken, recipeId: recipeId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func fetchPlannedMeals() async -> [RemotePlannedMeal] {
        guard let accessToken = tokens?.accessToken else { return [] }

        do {
            return try await client.plannedMeals(accessToken: accessToken)
        } catch {
            errorMessage = error.localizedDescription
            return []
        }
    }

    func savePlannedMeal(recipeId: UUID, dayOfWeek: Int, mealSlot: String) async -> RemotePlannedMeal? {
        guard let accessToken = tokens?.accessToken else { return nil }

        do {
            return try await client.savePlannedMeal(
                accessToken: accessToken,
                payload: PlannedMealRequest(
                    recipeId: recipeId,
                    dayOfWeek: dayOfWeek,
                    mealSlot: mealSlot
                )
            )
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func deletePlannedMeal(id: UUID) async {
        guard let accessToken = tokens?.accessToken else { return }

        do {
            try await client.deletePlannedMeal(accessToken: accessToken, plannedMealId: id)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func logout() async {
        let refreshToken = tokens?.refreshToken
        user = nil
        onboardingProfile = nil
        tokens = nil
        tokenStore.clear()

        if let refreshToken {
            try? await client.logout(refreshToken: refreshToken)
        }
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
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    private func updateOnboarding(
        operation: (String) async throws -> OnboardingProfile
    ) async -> Bool {
        guard let accessToken = tokens?.accessToken else {
            errorMessage = "Your session has expired. Please sign in again."
            return false
        }

        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            onboardingProfile = try await operation(accessToken)
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }
}
