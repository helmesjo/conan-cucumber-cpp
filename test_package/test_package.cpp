#include <cstdlib>
#include <iostream>

#include <cucumber-cpp/generic.hpp>
#include <cucumber-cpp/autodetect.hpp>

using cucumber::ScenarioScope;

struct MyContext {
    int result;
};

GIVEN("^Given value (\\d+)$") {
    REGEX_PARAM(int, val);
    ScenarioScope<MyContext> context;
    context->result = val;
}

WHEN("^When I add (\\d+)$") {
    REGEX_PARAM(int, val);
    ScenarioScope<MyContext> context;
    context->result += val;
}

THEN("^Then it equals (\\d+)$") {
    REGEX_PARAM(int, val);
    ScenarioScope<MyContext> context;
    //EXPECT_EQ(context->result, val);
}

int main()
{
    std::cout << "Bincrafters\n";
    return EXIT_SUCCESS;
}
